"""Main task runner: orchestrates terraform pipeline."""

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from .utils import (
    log_info, log_error, log_warn,
    export_localstack_env, check_localstack,
    load_spec, get_var, run_command
)
from .checks import run_checks


class TaskRunner:
    """Runs a terraform task through the full pipeline."""
    
    FAILURE_CATEGORIES = [
        "SYNTAX", "INIT", "VALIDATE", "PLAN", "APPLY",
        "CHECKS", "IDEMPOTENCY", "DESTROY", "LOCALSTACK"
    ]
    
    def __init__(self, model_name: str, task_id: str, run_id: str, 
                 generated_dir: Path, results_dir: Path):
        """Initialize the task runner.
        
        Args:
            model_name: Name of the model being tested.
            task_id: Task identifier.
            run_id: Unique run identifier.
            generated_dir: Base directory for generated terraform files.
            results_dir: Base directory for results.
        """
        self.model_name = model_name
        self.task_id = task_id
        self.run_id = run_id
        self.generated_dir = generated_dir
        self.results_dir = results_dir
        
        self.work_dir = generated_dir / model_name / task_id / run_id
        self.result_dir = results_dir / model_name / task_id / run_id
        self.logs_dir = self.result_dir / "logs"
        
        # Create directories
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Load task spec
        spec_file = Path(f"tasks/terraform_generation/{task_id}/spec.yaml")
        if not spec_file.exists():
            raise FileNotFoundError(f"Spec file not found: {spec_file}")
        self.spec = load_spec(spec_file)
        
        # Build terraform variable arguments from spec
        self.tf_vars = self._build_tf_vars()
    
    # Var names whose values are AWS resource names — must be unique per run
    # to avoid collisions when the same task runs concurrently for different models.
    _NAME_VARS = frozenset({"role_name", "policy_name", "bucket_name"})

    def _build_tf_vars(self) -> List[str]:
        """Build terraform -var arguments from spec.

        String vars listed in ``_NAME_VARS`` get a short unique suffix
        (derived from model_name + run_id) so that concurrent runs of the
        same task against different models don't collide in LocalStack.

        Returns:
            List of -var arguments for terraform commands.
        """
        import hashlib
        import json

        suffix = hashlib.sha1(
            f"{self.model_name}-{self.run_id}".encode()
        ).hexdigest()[:8]

        vars_list = []
        vars_dict = self.spec.get('vars', {})

        for key, value in vars_dict.items():
            if isinstance(value, list):
                vars_list.extend(["-var", f"{key}={json.dumps(value)}"])
            elif key in self._NAME_VARS and isinstance(value, str):
                vars_list.extend(["-var", f"{key}={value}-{suffix}"])
            else:
                vars_list.extend(["-var", f"{key}={value}"])

        return vars_list
    
    def _log_command(self, cmd: List[str], output: str, log_file: Path) -> None:
        """Log command output to file."""
        with open(log_file, 'w') as f:
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"{'='*80}\n")
            f.write(output)
    
    def _run_terraform(self, cmd: List[str], step_name: str, 
                      capture_output: bool = True,
                      timeout: Optional[int] = None) -> Tuple[bool, str, Optional[int]]:
        """Run a terraform command.
        
        Args:
            cmd: Terraform command to run.
            step_name: Name of the step (for logging).
            capture_output: Whether to capture output.
            timeout: Timeout in seconds (default: 300s for apply/destroy, 60s for others).
        
        Returns:
            Tuple of (success, output, exit_code)
        """
        # Set default timeouts based on step type
        if timeout is None:
            if step_name in ("apply", "apply_2", "destroy"):
                timeout = 300  # 5 minutes for apply/destroy operations
            elif step_name in ("plan", "plan_2"):
                timeout = 300  # 5 minutes for plan operations (can be slow with complex configs)
            elif step_name == "init":
                timeout = 180  # 3 minutes for init (provider download + cache lock contention)
            else:
                timeout = 60  # 1 minute for other operations
        
        log_file = self.logs_dir / f"terraform_{step_name}.txt"
        try:
            result = run_command(
                cmd,
                cwd=self.work_dir,
                capture_output=capture_output,
                check=False,
                timeout=timeout
            )
            output = result.stdout + result.stderr if capture_output else ""
            self._log_command(cmd, output, log_file)
            return result.returncode == 0, output, result.returncode
        except subprocess.TimeoutExpired:
            error_msg = f"Terraform {step_name} timed out after {timeout}s"
            log_error(error_msg)
            with open(log_file, 'w') as f:
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Error: {error_msg}\n")
                f.write(f"Timeout: {timeout}s\n")
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Exception running terraform {step_name}: {e}"
            log_error(error_msg)
            with open(log_file, 'w') as f:
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Error: {error_msg}\n")
            return False, error_msg, None
    
    def run(self) -> Dict[str, Any]:
        """Run the full task pipeline.
        
        Returns:
            Dictionary with result summary.
        """
        start_time = time.time()
        result = {
            "model_name": self.model_name,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "pass": False,
            "failure_category": None,
            "timings": {},
            "tool_exit_codes": {},
            "logs": {}
        }
        
        log_info(f"Starting task run: {self.task_id} (run: {self.run_id})")
        
        # Check LocalStack
        if not check_localstack():
            result["failure_category"] = "LOCALSTACK"
            result["pass"] = False
            return result
        
        # Export environment
        export_localstack_env()
        
        # Step 1: terraform fmt (format files first)
        log_info("Step 1: Running terraform fmt...")
        step_start = time.time()
        success, output, exit_code = self._run_terraform(
            ["terraform", "fmt"],
            "fmt"
        )
        result["timings"]["fmt"] = time.time() - step_start
        result["tool_exit_codes"]["fmt"] = exit_code
        result["logs"]["fmt"] = str(self.logs_dir / "terraform_fmt.txt")
        
        # Formatting should always succeed (it just formats files)
        # If it fails, it's a real error
        if not success:
            result["failure_category"] = "SYNTAX"
            result["pass"] = False
            return result
        
        # Step 1b: terraform fmt -check (verify formatting)
        log_info("Step 1b: Verifying formatting with terraform fmt -check...")
        step_start = time.time()
        success, output, exit_code = self._run_terraform(
            ["terraform", "fmt", "-check"],
            "fmt_check"
        )
        result["timings"]["fmt_check"] = time.time() - step_start
        result["tool_exit_codes"]["fmt_check"] = exit_code
        result["logs"]["fmt_check"] = str(self.logs_dir / "terraform_fmt_check.txt")
        
        # After formatting, check should pass, but if it doesn't, it's a syntax issue
        if not success:
            result["failure_category"] = "SYNTAX"
            result["pass"] = False
            return result
        
        # Step 2: terraform init
        log_info("Step 2: Running terraform init...")
        step_start = time.time()
        success, output, exit_code = self._run_terraform(
            ["terraform", "init"],
            "init"
        )
        result["timings"]["init"] = time.time() - step_start
        result["tool_exit_codes"]["init"] = exit_code
        result["logs"]["init"] = str(self.logs_dir / "terraform_init.txt")
        
        if not success:
            result["failure_category"] = "INIT"
            result["pass"] = False
            return result
        
        # Step 3: terraform validate
        log_info("Step 3: Running terraform validate...")
        step_start = time.time()
        success, output, exit_code = self._run_terraform(
            ["terraform", "validate"],
            "validate"
        )
        result["timings"]["validate"] = time.time() - step_start
        result["tool_exit_codes"]["validate"] = exit_code
        result["logs"]["validate"] = str(self.logs_dir / "terraform_validate.txt")
        
        if not success:
            result["failure_category"] = "VALIDATE"
            result["pass"] = False
            return result
        
        # Step 4: terraform plan
        log_info("Step 4: Running terraform plan...")
        step_start = time.time()
        plan_cmd = ["terraform", "plan", "-out", "plan.bin"] + self.tf_vars
        success, output, exit_code = self._run_terraform(
            plan_cmd,
            "plan"
        )
        result["timings"]["plan"] = time.time() - step_start
        result["tool_exit_codes"]["plan"] = exit_code
        result["logs"]["plan"] = str(self.logs_dir / "terraform_plan.txt")
        
        # Save plan output
        plan_file = self.result_dir / "terraform_plan.txt"
        with open(plan_file, 'w') as f:
            f.write(output)
        
        if not success:
            result["failure_category"] = "PLAN"
            result["pass"] = False
            return result
        
        # Step 5: terraform apply
        log_info("Step 5: Running terraform apply...")
        step_start = time.time()
        success, output, exit_code = self._run_terraform(
            ["terraform", "apply", "-auto-approve", "plan.bin"],
            "apply"
        )
        result["timings"]["apply"] = time.time() - step_start
        result["tool_exit_codes"]["apply"] = exit_code
        result["logs"]["apply"] = str(self.logs_dir / "terraform_apply.txt")
        
        # Save apply output
        apply_file = self.result_dir / "terraform_apply.txt"
        with open(apply_file, 'w') as f:
            f.write(output)
        
        if not success:
            result["failure_category"] = "APPLY"
            result["pass"] = False
            return result
        
        # Step 6: Get outputs
        log_info("Step 6: Getting terraform outputs...")
        success, output, exit_code = self._run_terraform(
            ["terraform", "output", "-json"],
            "output"
        )
        if success:
            outputs_file = self.work_dir / "outputs.json"
            with open(outputs_file, 'w') as f:
                f.write(output)
        
        # Step 7: Run checks
        log_info("Step 7: Running post-apply checks...")
        step_start = time.time()
        try:
            check_result = run_checks(self.work_dir, self.task_id)
            result["timings"]["checks"] = time.time() - step_start
            result["check_result"] = check_result
            
            check_file = self.result_dir / "check.json"
            with open(check_file, 'w') as f:
                json.dump(check_result, f, indent=2)
            
            if not check_result.get("pass", False):
                result["failure_category"] = "CHECKS"
                result["pass"] = False
                return result
        except Exception as e:
            log_error(f"Checks failed with exception: {e}")
            result["failure_category"] = "CHECKS"
            result["pass"] = False
            return result
        
        # Step 8: Second apply (idempotency check)
        # Use plan first to check for changes (faster than full apply)
        log_info("Step 8: Running second plan (idempotency check)...")
        step_start = time.time()
        plan_2_cmd = ["terraform", "plan"] + self.tf_vars
        success, output, exit_code = self._run_terraform(
            plan_2_cmd,
            "plan_2",
            timeout=120  # 2 minutes should be enough for a plan
        )
        result["timings"]["plan_2"] = time.time() - step_start
        result["tool_exit_codes"]["plan_2"] = exit_code
        result["logs"]["plan_2"] = str(self.logs_dir / "terraform_plan_2.txt")
        
        # Save second plan output
        plan_2_file = self.result_dir / "terraform_plan_2.txt"
        with open(plan_2_file, 'w') as f:
            f.write(output)
        
        # Check for idempotency - if plan shows no changes, we're good
        if not success:
            log_warn("Second plan failed - checking if it's a timeout or real error")
            # If it's a timeout, still check the output we got
            if "timed out" in output.lower():
                result["failure_category"] = "IDEMPOTENCY"
                result["pass"] = False
                return result
        
        # Check if plan shows changes
        if "No changes" not in output and "0 to add, 0 to change, 0 to destroy" not in output:
            log_warn("Second plan shows changes - idempotency check failed")
            result["failure_category"] = "IDEMPOTENCY"
            result["pass"] = False
            return result
        result["timings"]["apply_2"] = time.time() - step_start
        result["tool_exit_codes"]["apply_2"] = exit_code
        result["logs"]["apply_2"] = str(self.logs_dir / "terraform_apply_2.txt")
        
        # Save second apply output
        apply_2_file = self.result_dir / "terraform_apply_2.txt"
        with open(apply_2_file, 'w') as f:
            f.write(output)
        
        # Check for idempotency
        if "No changes" not in output and "Apply complete!" not in output:
            log_warn("Second apply shows changes - idempotency check failed")
            result["failure_category"] = "IDEMPOTENCY"
            result["pass"] = False
            return result
        
        # Step 9: terraform destroy
        log_info("Step 9: Running terraform destroy...")
        step_start = time.time()
        success, output, exit_code = self._run_terraform(
            ["terraform", "destroy", "-auto-approve"],
            "destroy"
        )
        result["timings"]["destroy"] = time.time() - step_start
        result["tool_exit_codes"]["destroy"] = exit_code
        result["logs"]["destroy"] = str(self.logs_dir / "terraform_destroy.txt")
        
        # Save destroy output
        destroy_file = self.result_dir / "terraform_destroy.txt"
        with open(destroy_file, 'w') as f:
            f.write(output)
        
        if not success:
            result["failure_category"] = "DESTROY"
            result["pass"] = False
            return result
        
        # All steps passed!
        result["pass"] = True
        result["timings"]["total"] = time.time() - start_time
        
        log_info(f"Task completed successfully in {result['timings']['total']:.2f}s")
        
        return result

