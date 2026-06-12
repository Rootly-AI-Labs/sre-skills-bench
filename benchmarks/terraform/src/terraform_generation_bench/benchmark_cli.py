#!/usr/bin/env python3
"""CLI tool for running LLM Terraform benchmarks."""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Ensure we can import from current directory
sys.path.insert(0, str(Path(__file__).parent))

from terraform_generation_bench.benchmark import BenchmarkRunner
from terraform_generation_bench.report_generator import ReportGenerator


def main():
    """Main CLI entry point."""
    # Load environment variables from .env file if present
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run LLM Terraform code generation benchmarks"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List models command
    list_parser = subparsers.add_parser("list-models", help="List available OpenRouter models")
    list_parser.add_argument("--provider", choices=["openrouter"], default="openrouter",
                            help="Provider to list models for (default: openrouter)")
    list_parser.add_argument("--filter", help="Filter models by name (e.g., 'gemini', 'llama')")
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate Terraform code using LLM")
    gen_parser.add_argument("--provider", required=True, choices=["openai", "anthropic", "openrouter"],
                           help="LLM provider")
    gen_parser.add_argument("--model", required=True, help="Model name")
    gen_parser.add_argument("--task-id", required=True, help="Task identifier")
    gen_parser.add_argument("--run-id", help="Run identifier (auto-generated if not provided)")
    
    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run benchmark for a model")
    bench_parser.add_argument("--provider", required=True, choices=["openai", "anthropic", "openrouter"],
                             help="LLM provider")
    bench_parser.add_argument("--model", required=True, help="Model name")
    bench_parser.add_argument("--task-id", required=True, help="Task identifier")
    bench_parser.add_argument("--run-id", help="Run identifier")
    
    # Suite command
    suite_parser = subparsers.add_parser("suite", help="Run benchmark suite")
    suite_parser.add_argument("--models", dest="models",
                             help="JSON file with model configurations (default: models.json)")
    suite_parser.add_argument("--models-file", dest="models",
                             help="Alias for --models")
    suite_parser.add_argument("--tasks", nargs="+",
                             help="Task IDs to test (default: all tasks in tasks/)")
    suite_parser.add_argument("--runs-per-model", type=int, default=1,
                             help="Number of runs per model (default: 1)")
    suite_parser.add_argument("--max-workers", type=int, default=10,
                             help="Maximum parallel workers (default: 10)")
    suite_parser.add_argument("--no-tui", action="store_true",
                             help="Disable the Rich TUI (plain log output)")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate reports")
    report_parser.add_argument("--task-id", help="Task identifier (default: all tasks with results)")
    report_parser.add_argument("--models", nargs="+", help="Model names to compare")
    report_parser.add_argument("--format", choices=["json", "html", "markdown", "table", "comprehensive", "summary"],
                              default="markdown", help="Report format (comprehensive shows overall + per-task, summary shows per-task matrix)")
    report_parser.add_argument("--output", help="Output file path (for single task) or directory (for all tasks)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    base_dir = Path(__file__).parent.parent.parent
    results_dir = base_dir / "results"
    runner = BenchmarkRunner()
    reporter = ReportGenerator(results_dir=results_dir)
    
    if args.command == "list-models":
        from terraform_generation_bench.llm_client import OpenRouterClient
        import os
        
        if args.provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                print("Error: OPENROUTER_API_KEY not set")
                print("Set it with: export OPENROUTER_API_KEY='your-key-here'")
                sys.exit(1)
            
            print("Fetching available models from OpenRouter...")
            models = OpenRouterClient.get_available_models(api_key)
            
            if not models:
                print("Error: Could not fetch models. Check your API key.")
                sys.exit(1)
            
            if args.filter:
                models = [m for m in models if args.filter.lower() in m.lower()]
                print(f"\nFiltered models (containing '{args.filter}'):")
            else:
                print(f"\nAvailable models ({len(models)} total):")
            
            for model in sorted(models):
                print(f"  {model}")
            
            print(f"\nTip: Use --filter to search (e.g., --filter gemini)")
            sys.exit(0)
    
    if args.command == "generate":
        from terraform_generation_bench.terraform_generator import TerraformGenerator
        from terraform_generation_bench.llm_client import LLMClientFactory
        
        # Load prompt from tasks directory
        prompt_file = Path(__file__).parent.parent.parent / "tasks" / "terraform_generation" / args.task_id / "prompt.txt"
        if not prompt_file.exists():
            prompt_file = Path.cwd() / "tasks" / args.task_id / "prompt.txt"
        if not prompt_file.exists():
            print(f"Error: Prompt file not found: tasks/{args.task_id}/prompt.txt")
            sys.exit(1)
        
        print(f"Loading prompt from: {prompt_file}")
        with open(prompt_file, 'r') as f:
            prompt = f.read()
        
        # Generate code using the prompt text
        print(f"Generating Terraform code with {args.provider}/{args.model}...")
        llm_client = LLMClientFactory.create_client(args.provider, args.model)
        generator = TerraformGenerator(llm_client)
        files = generator.generate(prompt, args.task_id)
        
        run_id = args.run_id or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # Replace both - and / with _ for valid directory names
        model_name = f"{args.provider}_{args.model.replace('-', '_').replace('/', '_')}"
        work_dir = Path(__file__).parent.parent.parent / "generated" / model_name / args.task_id / run_id
        work_dir.mkdir(parents=True, exist_ok=True)
        
        generator.save_files(files, work_dir)
        print(f"\nGenerated Terraform files in: {work_dir}")
        print(f"Files: {', '.join(files.keys())}")
    
    elif args.command == "benchmark":
        result = runner.run_single_benchmark(
            args.provider, args.model, args.task_id, args.run_id
        )
        
        print("\n" + "="*80)
        print("BENCHMARK RESULT")
        print("="*80)
        print(f"Model: {result['model_name']}")
        print(f"Task: {result['task_id']}")
        print(f"Status: {'PASS' if result['overall_pass'] else 'FAIL'}")
        if result.get('error'):
            print(f"Error: {result['error']}")
        print(f"Total Time: {result.get('total_time', 0):.2f}s")
        print("="*80)
        
        sys.exit(0 if result['overall_pass'] else 1)
    
    elif args.command == "suite":
        # Load models from JSON file
        if not args.models:
            # Try default models.json
            models_file = Path("models.json")
            if not models_file.exists():
                print("Error: --models required (or create models.json)")
                sys.exit(1)
            args.models = str(models_file)
        
        with open(args.models, 'r') as f:
            models_config = json.load(f)
        
        if isinstance(models_config, list):
            models = models_config
        elif isinstance(models_config, dict) and "models" in models_config:
            models = models_config["models"]
        else:
            print("Error: Invalid models JSON format")
            sys.exit(1)
        
        # Auto-discover tasks if not provided
        if not args.tasks:
            tasks_dir = Path(__file__).parent.parent.parent / "tasks" / "terraform_generation"
            if not tasks_dir.exists():
                print("Error: tasks/ directory not found")
                sys.exit(1)
            args.tasks = [d.name for d in tasks_dir.iterdir() if d.is_dir() and (d / "spec.yaml").exists()]
            if not args.tasks:
                print("Error: No tasks found in tasks/ directory")
                sys.exit(1)
            print(f"Auto-discovered {len(args.tasks)} tasks: {', '.join(args.tasks)}")
        
        # Set up TUI display if stderr is a TTY and --no-tui not passed
        display = None
        if sys.stderr.isatty() and not args.no_tui:
            from terraform_generation_bench.display import (
                BenchmarkDisplay,
                set_log_callback,
            )
            total_jobs = len(models) * len(args.tasks) * args.runs_per_model
            display = BenchmarkDisplay(total_jobs)
            set_log_callback(display.on_log)

        # Run benchmark suite with multiple runs per model
        all_results = []
        try:
            for run_num in range(args.runs_per_model):
                if args.runs_per_model > 1:
                    print(f"\n{'='*80}")
                    print(f"Run {run_num + 1} of {args.runs_per_model}")
                    print(f"{'='*80}")
                suite_result = runner.run_benchmark_suite(
                    models, args.tasks,
                    max_workers=args.max_workers,
                    display=display,
                )
                all_results.append(suite_result)
        finally:
            if display is not None:
                from terraform_generation_bench.display import set_log_callback
                set_log_callback(None)
        
        # Aggregate results if multiple runs
        if args.runs_per_model > 1:
            total_runs = sum(len(r['results']) for r in all_results)
            total_time = sum(r['total_time'] for r in all_results)
            suite_result = {
                'results': [r for suite_r in all_results for r in suite_r['results']],
                'total_time': total_time,
                'runs_per_model': args.runs_per_model
            }
        
        print("\n" + "="*80)
        print("BENCHMARK SUITE COMPLETE")
        print("="*80)
        print(f"Models tested: {len(models)}")
        print(f"Tasks tested: {len(args.tasks)}")
        print(f"Total runs: {len(suite_result['results'])}")
        print(f"Total time: {suite_result['total_time']:.2f}s")
        print("="*80)

        # Print model comparison table
        from collections import defaultdict
        model_stats = defaultdict(lambda: {"pass": 0, "fail": 0, "total": 0})
        for r in suite_result["results"]:
            name = r.get("model_name") or f"{r.get('provider', '?')}_{r.get('model', '?')}"
            model_stats[name]["total"] += 1
            if r.get("overall_pass"):
                model_stats[name]["pass"] += 1
            else:
                model_stats[name]["fail"] += 1

        if model_stats:
            # Sort by pass rate descending
            ranked = sorted(
                model_stats.items(),
                key=lambda kv: kv[1]["pass"] / max(kv[1]["total"], 1),
                reverse=True,
            )
            name_width = max(len(n) for n, _ in ranked)
            name_width = max(name_width, 5)  # minimum width for "Model"
            header = f"{'Model':<{name_width}}  {'Pass':>5}  {'Fail':>5}  {'Total':>5}  {'Acc':>7}"
            print(f"\n{header}")
            print("-" * len(header))
            for name, stats in ranked:
                acc = stats["pass"] / max(stats["total"], 1) * 100
                print(f"{name:<{name_width}}  {stats['pass']:>5}  {stats['fail']:>5}  {stats['total']:>5}  {acc:>6.1f}%")
            print()
    
    elif args.command == "report":
        # Handle comprehensive and summary reports (across all tasks)
        if args.format in ("comprehensive", "summary"):
            comprehensive = reporter.generate_comprehensive_report(
                models=args.models,
                task_ids=None  # Auto-discover all tasks
            )

            if args.format == "summary":
                # Matrix table: models x tasks
                output_file = None
                if args.output:
                    output_file = Path(args.output).with_suffix(".txt")
                table = reporter.generate_comprehensive_table_report(comprehensive, output_file)
                print(table)
                if output_file:
                    print(f"Saved to: {output_file}")
                return

            if args.output:
                output_file = Path(args.output)
            else:
                output_file = base_dir / "reports" / f"comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Generate in requested format
            if args.output and args.output.endswith('.html'):
                output_file = Path(args.output)
                reporter.generate_comprehensive_html_report(comprehensive, output_file)
            else:
                output_file = output_file.with_suffix(".md")
                reporter.generate_comprehensive_markdown_report(comprehensive, output_file)

            print(f"\n✅ Comprehensive report generated: {output_file}")
            print(f"\nOverall Model Rankings:")
            for i, entry in enumerate(comprehensive.get("ranking", [])[:5], 1):
                stats = comprehensive["models"][entry["model"]]
                print(f"  {i}. {entry['model']}: {stats['overall_pass_rate']}% pass rate ({stats['total_runs']} runs)")
            return
        
        # Auto-discover tasks if not provided
        if not args.task_id:
            results_dir = Path(__file__).parent.parent.parent / "results"
            if not results_dir.exists():
                print("Error: results/ directory not found. Run benchmarks first.")
                sys.exit(1)
            
            # Find all tasks that have results
            # Results are stored as: results/{model}/{task}/{run}/benchmark_result.json
            tasks_with_results = set()
            for model_dir in results_dir.iterdir():
                if model_dir.is_dir():
                    for task_dir in model_dir.iterdir():
                        if task_dir.is_dir():
                            # Check if any run directory has benchmark_result.json
                            for run_dir in task_dir.iterdir():
                                if run_dir.is_dir():
                                    if (run_dir / "benchmark_result.json").exists():
                                        tasks_with_results.add(task_dir.name)
                                        break  # Found at least one result for this task
            
            if not tasks_with_results:
                print("Error: No benchmark results found. Run benchmarks first.")
                sys.exit(1)
            
            args.task_id = list(tasks_with_results)
            print(f"Auto-discovered {len(args.task_id)} tasks with results: {', '.join(args.task_id)}")
        
        # Handle single task or multiple tasks
        if isinstance(args.task_id, str):
            task_ids = [args.task_id]
        else:
            task_ids = args.task_id
        
        # Generate reports for each task
        reports_dir = Path(__file__).parent.parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        for task_id in task_ids:
            print(f"\nGenerating report for {task_id}...")
            
            if args.models:
                comparison = reporter.generate_comparison_report(args.models, task_id)
            else:
                # Find all models that have results for this task
                results_dir = Path(__file__).parent.parent.parent / "results"
                models = []
                for model_dir in results_dir.iterdir():
                    if model_dir.is_dir():
                        task_dir = model_dir / task_id
                        if task_dir.exists() and task_dir.is_dir():
                            # Check if any run directory has benchmark_result.json
                            has_results = False
                            for run_dir in task_dir.iterdir():
                                if run_dir.is_dir() and (run_dir / "benchmark_result.json").exists():
                                    has_results = True
                                    break
                            if has_results:
                                models.append(model_dir.name)
                
                if not models:
                    print(f"  Warning: No results found for task: {task_id}, skipping...")
                    continue
                
                comparison = reporter.generate_comparison_report(models, task_id)
            
            # Generate report in requested format
            if args.output:
                if len(task_ids) == 1:
                    # Single task - use provided output path
                    output_file = Path(args.output)
                else:
                    # Multiple tasks - use output as directory
                    output_dir = Path(args.output)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = output_dir / f"{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else:
                output_file = reports_dir / f"{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if args.format == "json":
                output_file = output_file.with_suffix(".json")
                with open(output_file, 'w') as f:
                    json.dump(comparison, f, indent=2)
            elif args.format == "html":
                output_file = output_file.with_suffix(".html")
                reporter.generate_html_report(comparison, output_file)
            elif args.format == "table":
                output_file = output_file.with_suffix(".txt")
                reporter.generate_table_report(comparison, output_file)
            else:  # markdown
                output_file = output_file.with_suffix(".md")
                reporter.generate_markdown_report(comparison, output_file)
            
            print(f"  Report generated: {output_file}")
        
        if len(task_ids) > 1:
            print(f"\n✅ Generated {len(task_ids)} reports in {reports_dir}")


if __name__ == "__main__":
    from datetime import datetime
    main()

