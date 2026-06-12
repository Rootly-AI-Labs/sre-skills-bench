"""Report generator for benchmark results."""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class ReportGenerator:
    """Generates reports from benchmark results."""
    
    def __init__(self, results_dir: Path = None):
        """Initialize report generator.
        
        Args:
            results_dir: Directory containing benchmark results
        """
        self.results_dir = results_dir
    
    def load_benchmark_results(self, model_name: str, task_id: str, 
                              run_id: str) -> Dict[str, Any]:
        """Load benchmark result for a specific run.
        
        Args:
            model_name: Model name
            task_id: Task ID
            run_id: Run ID
            
        Returns:
            Benchmark result dictionary
        """
        result_file = self.results_dir / model_name / task_id / run_id / "benchmark_result.json"
        if not result_file.exists():
            return {}
        
        with open(result_file, 'r') as f:
            return json.load(f)
    
    def generate_model_report(self, model_name: str, task_id: str, latest_n: int = 1) -> Dict[str, Any]:
        """Generate report for a specific model and task.

        Args:
            model_name: Model name
            task_id: Task ID
            latest_n: Use only the N most recent runs (default: 1). 0 means all.

        Returns:
            Report dictionary
        """
        task_dir = self.results_dir / model_name / task_id

        if not task_dir.exists():
            return {"error": "No results found"}

        runs = []
        run_dirs = []
        for run_dir in task_dir.iterdir():
            if run_dir.is_dir():
                result = self.load_benchmark_results(model_name, task_id, run_dir.name)
                if result:
                    runs.append(result)
                    run_dirs.append((run_dir.name, result))

        if not runs:
            return {"error": "No valid runs found"}

        # Keep only the N most recent runs (by run_id timestamp)
        if latest_n and len(runs) > latest_n:
            run_dirs.sort(key=lambda x: x[0], reverse=True)
            run_dirs = run_dirs[:latest_n]
            runs = [result for _, result in run_dirs]
        
        # Calculate statistics
        total_runs = len(runs)
        passed_runs = sum(1 for r in runs if r.get("overall_pass", False))
        pass_rate = (passed_runs / total_runs) * 100 if total_runs > 0 else 0
        
        avg_time = sum(r.get("total_time", 0) for r in runs) / total_runs if total_runs > 0 else 0
        
        # Failure categories
        failure_categories = {}
        for run in runs:
            category = run.get("steps", {}).get("terraform", {}).get("failure_category")
            if category:
                failure_categories[category] = failure_categories.get(category, 0) + 1
        
        return {
            "model_name": model_name,
            "task_id": task_id,
            "total_runs": total_runs,
            "passed_runs": passed_runs,
            "pass_rate": round(pass_rate, 2),
            "average_time": round(avg_time, 2),
            "failure_categories": failure_categories,
            "runs": runs
        }
    
    def generate_comparison_report(self, models: List[str], task_id: str) -> Dict[str, Any]:
        """Generate comparison report across multiple models.
        
        Args:
            models: List of model names
            task_id: Task ID
            
        Returns:
            Comparison report dictionary
        """
        comparison = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "models": {}
        }
        
        for model_name in models:
            report = self.generate_model_report(model_name, task_id)
            if "error" not in report:
                comparison["models"][model_name] = {
                    "pass_rate": report["pass_rate"],
                    "average_time": report["average_time"],
                    "total_runs": report["total_runs"],
                    "passed_runs": report["passed_runs"],
                    "failure_categories": report["failure_categories"]
                }
        
        # Rank models by pass rate, then by average time
        ranked = sorted(
            comparison["models"].items(),
            key=lambda x: (-x[1]["pass_rate"], x[1]["average_time"])
        )
        comparison["ranking"] = [{"model": name, **stats} for name, stats in ranked]
        
        return comparison
    
    def generate_html_report(self, comparison: Dict[str, Any], output_file: Path) -> None:
        """Generate HTML report from comparison data.
        
        Args:
            comparison: Comparison report dictionary
            output_file: Output HTML file path
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Terraform LLM Benchmark Report - {comparison['task_id']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .pass {{ color: green; font-weight: bold; }}
        .fail {{ color: red; font-weight: bold; }}
        .ranking {{ background-color: #e7f3ff; padding: 15px; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Terraform LLM Benchmark Report</h1>
    <p><strong>Task:</strong> {comparison['task_id']}</p>
    <p><strong>Generated:</strong> {comparison['timestamp']}</p>
    
    <h2>Model Comparison</h2>
    <table>
        <tr>
            <th>Rank</th>
            <th>Model</th>
            <th>Pass Rate</th>
            <th>Avg Time (s)</th>
            <th>Total Runs</th>
            <th>Passed Runs</th>
        </tr>
"""
        
        for i, entry in enumerate(comparison.get("ranking", []), 1):
            model = entry["model"]
            stats = comparison["models"][model]
            pass_class = "pass" if stats["pass_rate"] >= 50 else "fail"
            
            html += f"""
        <tr>
            <td>{i}</td>
            <td>{model}</td>
            <td class="{pass_class}">{stats['pass_rate']}%</td>
            <td>{stats['average_time']}</td>
            <td>{stats['total_runs']}</td>
            <td>{stats['passed_runs']}</td>
        </tr>
"""
        
        html += """
    </table>
    
    <h2>Failure Categories</h2>
    <table>
        <tr>
            <th>Model</th>
            <th>Failure Category</th>
            <th>Count</th>
        </tr>
"""
        
        for model_name, stats in comparison["models"].items():
            for category, count in stats.get("failure_categories", {}).items():
                html += f"""
        <tr>
            <td>{model_name}</td>
            <td>{category}</td>
            <td>{count}</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(html)
    
    def generate_markdown_report(self, comparison: Dict[str, Any], output_file: Path) -> None:
        """Generate Markdown report from comparison data.
        
        Args:
            comparison: Comparison report dictionary
            output_file: Output Markdown file path
        """
        md = f"""# Terraform LLM Benchmark Report

**Task:** {comparison['task_id']}  
**Generated:** {comparison['timestamp']}

## Model Comparison

| Rank | Model | Pass Rate | Avg Time (s) | Total Runs | Passed Runs |
|------|-------|-----------|--------------|------------|-------------|
"""
        
        for i, entry in enumerate(comparison.get("ranking", []), 1):
            model = entry["model"]
            stats = comparison["models"][model]
            md += f"| {i} | {model} | {stats['pass_rate']}% | {stats['average_time']} | {stats['total_runs']} | {stats['passed_runs']} |\n"
        
        md += "\n## Failure Categories\n\n"
        md += "| Model | Failure Category | Count |\n"
        md += "|-------|------------------|-------|\n"
        
        for model_name, stats in comparison["models"].items():
            for category, count in stats.get("failure_categories", {}).items():
                md += f"| {model_name} | {category} | {count} |\n"
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(md)
    
    def generate_table_report(self, comparison: Dict[str, Any], output_file: Path) -> None:
        """Generate simple ASCII table report from comparison data.
        
        Args:
            comparison: Comparison report dictionary
            output_file: Output text file path
        """
        # Calculate column widths
        max_model_len = max(len(entry["model"]) for entry in comparison.get("ranking", [])) if comparison.get("ranking") else 20
        max_model_len = max(max_model_len, 15)  # Minimum width for "Model" header
        
        # Header
        table = f"Terraform LLM Benchmark Report\n"
        table += f"{'='*80}\n"
        table += f"Task: {comparison['task_id']}\n"
        table += f"Generated: {comparison['timestamp']}\n"
        table += f"{'='*80}\n\n"
        
        # Model comparison table
        table += "Model Comparison\n"
        table += "-" * 80 + "\n"
        table += f"{'Rank':<6} {'Model':<{max_model_len}} {'Pass Rate':<12} {'Avg Time':<12} {'Runs':<8} {'Passed':<8}\n"
        table += "-" * 80 + "\n"
        
        for i, entry in enumerate(comparison.get("ranking", []), 1):
            model = entry["model"]
            stats = comparison["models"][model]
            pass_rate = f"{stats['pass_rate']}%"
            avg_time = f"{stats['average_time']:.2f}s"
            total_runs = str(stats['total_runs'])
            passed_runs = str(stats['passed_runs'])
            
            table += f"{i:<6} {model:<{max_model_len}} {pass_rate:<12} {avg_time:<12} {total_runs:<8} {passed_runs:<8}\n"
        
        table += "-" * 80 + "\n\n"
        
        # Failure categories
        has_failures = any(stats.get("failure_categories") for stats in comparison["models"].values())
        if has_failures:
            table += "Failure Categories\n"
            table += "-" * 80 + "\n"
            table += f"{'Model':<{max_model_len}} {'Category':<20} {'Count':<8}\n"
            table += "-" * 80 + "\n"
            
            for model_name, stats in comparison["models"].items():
                for category, count in stats.get("failure_categories", {}).items():
                    table += f"{model_name:<{max_model_len}} {category:<20} {count:<8}\n"
            
            table += "-" * 80 + "\n"
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(table)
    
    def generate_comprehensive_report(self, models: List[str] = None, task_ids: List[str] = None) -> Dict[str, Any]:
        """Generate comprehensive report across all models and tasks.
        
        Args:
            models: List of model names (auto-discovered if None)
            task_ids: List of task IDs (auto-discovered if None)
            
        Returns:
            Comprehensive report dictionary with overall and per-task stats
        """
        # Auto-discover models if not provided
        if models is None:
            # First, try to load from models.json to get all expected models
            models_json_path = Path(__file__).parent.parent.parent / "models.json"
            expected_models = set()
            if models_json_path.exists():
                try:
                    import json
                    with open(models_json_path, 'r') as f:
                        models_config = json.load(f)
                    for model_config in models_config:
                        provider = model_config.get("provider", "")
                        model = model_config.get("model", "")
                        # Generate model name using same logic as benchmark.py
                        model_name = f"{provider}_{model.replace('-', '_').replace('/', '_')}"
                        expected_models.add(model_name)
                except Exception as e:
                    # Fall back to directory discovery if models.json can't be read
                    pass
            
            # If we found models in models.json, use only those (to avoid old truncated names)
            # Otherwise, fall back to directory discovery
            if expected_models:
                models = sorted(list(expected_models))
            else:
                # Fallback: discover from results directory
                models = set()
                for model_dir in self.results_dir.iterdir():
                    if model_dir.is_dir():
                        models.add(model_dir.name)
                models = sorted(list(models))
        
        # Auto-discover tasks if not provided
        if task_ids is None:
            task_ids = set()
            for model_dir in self.results_dir.iterdir():
                if model_dir.is_dir():
                    for task_dir in model_dir.iterdir():
                        if task_dir.is_dir():
                            for run_dir in task_dir.iterdir():
                                if run_dir.is_dir() and (run_dir / "benchmark_result.json").exists():
                                    task_ids.add(task_dir.name)
                                    break
            task_ids = sorted(list(task_ids))
        
        comprehensive = {
            "timestamp": datetime.now().isoformat(),
            "models": {},
            "tasks": {},
            "overall": {}
        }
        
        # Collect data for each model
        for model_name in models:
            model_stats = {
                "total_runs": 0,
                "passed_runs": 0,
                "total_time": 0.0,
                "tasks": {}
            }
            
            # Collect per-task stats
            for task_id in task_ids:
                report = self.generate_model_report(model_name, task_id, latest_n=10)
                if "error" not in report:
                    # Get failure reason from the latest run
                    fail_reason = None
                    if report.get("runs"):
                        latest_run = report["runs"][0]
                        # Check for generation error
                        if latest_run.get("error"):
                            error_msg = latest_run['error']
                            # Extract key error info (model name, error type)
                            if "None of the tried models are available" in error_msg:
                                fail_reason = "Generation: Model not available"
                            elif "400 Client Error" in error_msg or "Bad Request" in error_msg:
                                # Extract model name from error if available
                                if "is not a valid model ID" in error_msg:
                                    fail_reason = "Generation: Invalid model ID"
                                else:
                                    fail_reason = "Generation: API Bad Request"
                            elif "404" in error_msg or "Not Found" in error_msg:
                                fail_reason = "Generation: Model not found"
                            elif "401" in error_msg or "Unauthorized" in error_msg:
                                fail_reason = "Generation: API auth error"
                            elif "402" in error_msg or "Payment Required" in error_msg:
                                fail_reason = "Generation: Insufficient credits"
                            else:
                                # Truncate to 80 chars for other errors
                                fail_reason = f"Generation: {error_msg[:80]}"
                        elif not latest_run.get("overall_pass", False):
                            # Check terraform failure category
                            failure_category = latest_run.get("steps", {}).get("terraform", {}).get("failure_category")
                            if failure_category:
                                fail_reason = failure_category
                            else:
                                fail_reason = "Unknown"
                    
                    model_stats["tasks"][task_id] = {
                        "pass_rate": report["pass_rate"],
                        "average_time": report["average_time"],
                        "total_runs": report["total_runs"],
                        "passed_runs": report["passed_runs"],
                        "fail_reason": fail_reason
                    }
                    model_stats["total_runs"] += report["total_runs"]
                    model_stats["passed_runs"] += report["passed_runs"]
                    model_stats["total_time"] += report["average_time"] * report["total_runs"]
                    
                    # Store overall fail reason (for models that failed all tasks)
                    if fail_reason and model_stats.get("overall_fail_reason") is None:
                        model_stats["overall_fail_reason"] = fail_reason
            
            # Calculate overall stats
            if model_stats["total_runs"] > 0:
                model_stats["overall_pass_rate"] = round((model_stats["passed_runs"] / model_stats["total_runs"]) * 100, 2)
                model_stats["average_time"] = round(model_stats["total_time"] / model_stats["total_runs"], 2)
            else:
                model_stats["overall_pass_rate"] = 0.0
                model_stats["average_time"] = 0.0
            
            comprehensive["models"][model_name] = model_stats
        
        # Collect per-task stats across all models
        for task_id in task_ids:
            task_stats = {
                "models": {},
                "best_model": None,
                "best_pass_rate": 0.0
            }
            
            for model_name in models:
                if task_id in comprehensive["models"][model_name]["tasks"]:
                    task_data = comprehensive["models"][model_name]["tasks"][task_id]
                    task_stats["models"][model_name] = task_data
                    if task_data["pass_rate"] > task_stats["best_pass_rate"]:
                        task_stats["best_pass_rate"] = task_data["pass_rate"]
                        task_stats["best_model"] = model_name
            
            comprehensive["tasks"][task_id] = task_stats
        
        # Rank models by overall pass rate
        ranked = sorted(
            comprehensive["models"].items(),
            key=lambda x: (-x[1]["overall_pass_rate"], x[1]["average_time"])
        )
        comprehensive["ranking"] = [{"model": name, **stats} for name, stats in ranked]
        
        return comprehensive
    
    def generate_comprehensive_html_report(self, comprehensive: Dict[str, Any], output_file: Path) -> None:
        """Generate comprehensive HTML report."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Terraform LLM Comprehensive Benchmark Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #f1f1f1; }}
        .pass {{ color: #28a745; font-weight: bold; }}
        .fail {{ color: #dc3545; font-weight: bold; }}
        .excellent {{ background-color: #d4edda; }}
        .good {{ background-color: #d1ecf1; }}
        .poor {{ background-color: #f8d7da; }}
        .task-section {{ margin: 30px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px; }}
        .summary-box {{ background-color: #e7f3ff; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #2196F3; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Terraform LLM Comprehensive Benchmark Report</h1>
        <p><strong>Generated:</strong> {comprehensive['timestamp']}</p>
        <p><strong>Models Tested:</strong> {len(comprehensive['models'])}</p>
        <p><strong>Tasks Tested:</strong> {len(comprehensive['tasks'])}</p>
        
        <div class="summary-box">
            <h2>📊 Overall Model Performance</h2>
            <table>
                <tr>
                    <th>Rank</th>
                    <th>Model</th>
                    <th>Overall Pass Rate</th>
                    <th>Avg Time (s)</th>
                    <th>Total Runs</th>
                    <th>Passed Runs</th>
                </tr>
"""
        
        for i, entry in enumerate(comprehensive.get("ranking", []), 1):
            model = entry["model"]
            stats = comprehensive["models"][model]
            pass_rate = stats["overall_pass_rate"]
            pass_class = "pass" if pass_rate >= 50 else "fail"
            row_class = "excellent" if pass_rate >= 80 else "good" if pass_rate >= 50 else "poor"
            
            html += f"""
                <tr class="{row_class}">
                    <td><strong>{i}</strong></td>
                    <td><strong>{model}</strong></td>
                    <td class="{pass_class}">{pass_rate}%</td>
                    <td>{stats['average_time']:.2f}</td>
                    <td>{stats['total_runs']}</td>
                    <td>{stats['passed_runs']}</td>
                </tr>
"""
        
        html += """
            </table>
        </div>
        
        <h2>📋 Per-Task Breakdown</h2>
"""
        
        for task_id, task_stats in comprehensive["tasks"].items():
            html += f"""
        <div class="task-section">
            <h3>Task: {task_id}</h3>
            <p><strong>Best Model:</strong> {task_stats.get('best_model', 'N/A')} ({task_stats.get('best_pass_rate', 0):.1f}%)</p>
            <table>
                <tr>
                    <th>Model</th>
                    <th>Pass Rate</th>
                    <th>Avg Time (s)</th>
                    <th>Runs</th>
                    <th>Passed</th>
                </tr>
"""
            
            # Sort models by pass rate for this task
            sorted_models = sorted(
                task_stats["models"].items(),
                key=lambda x: (-x[1]["pass_rate"], x[1]["average_time"])
            )
            
            for model_name, model_data in sorted_models:
                pass_rate = model_data["pass_rate"]
                pass_class = "pass" if pass_rate >= 50 else "fail"
                html += f"""
                <tr>
                    <td>{model_name}</td>
                    <td class="{pass_class}">{pass_rate}%</td>
                    <td>{model_data['average_time']:.2f}</td>
                    <td>{model_data['total_runs']}</td>
                    <td>{model_data['passed_runs']}</td>
                </tr>
"""
            
            html += """
            </table>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(html)
    
    def generate_comprehensive_markdown_report(self, comprehensive: Dict[str, Any], output_file: Path) -> None:
        """Generate comprehensive Markdown report."""
        md = f"""# 🚀 Terraform LLM Comprehensive Benchmark Report

**Generated:** {comprehensive['timestamp']}  
**Models Tested:** {len(comprehensive['models'])}  
**Tasks Tested:** {len(comprehensive['tasks'])}

## 📊 Overall Model Performance

| Rank | Model | Overall Pass Rate | Avg Time (s) | Total Runs | Passed Runs | Fail Reason |
|------|-------|------------------|---------------|------------|-------------|-------------|
"""
        
        for i, entry in enumerate(comprehensive.get("ranking", []), 1):
            model = entry["model"]
            stats = comprehensive["models"][model]
            fail_reason = stats.get("overall_fail_reason", "-" if stats['overall_pass_rate'] > 0 else "N/A")
            md += f"| {i} | {model} | {stats['overall_pass_rate']}% | {stats['average_time']:.2f} | {stats['total_runs']} | {stats['passed_runs']} | {fail_reason} |\n"
        
        md += "\n## 📋 Per-Task Breakdown\n\n"
        
        for task_id, task_stats in comprehensive["tasks"].items():
            md += f"### Task: {task_id}\n\n"
            md += f"**Best Model:** {task_stats.get('best_model', 'N/A')} ({task_stats.get('best_pass_rate', 0):.1f}%)\n\n"
            md += "| Model | Pass Rate | Avg Time (s) | Runs | Passed | Fail Reason |\n"
            md += "|-------|-----------|--------------|------|--------|------------|\n"
            
            sorted_models = sorted(
                task_stats["models"].items(),
                key=lambda x: (-x[1]["pass_rate"], x[1]["average_time"])
            )
            
            for model_name, model_data in sorted_models:
                fail_reason = model_data.get("fail_reason", "-" if model_data['pass_rate'] > 0 else "N/A")
                md += f"| {model_name} | {model_data['pass_rate']}% | {model_data['average_time']:.2f} | {model_data['total_runs']} | {model_data['passed_runs']} | {fail_reason} |\n"

            md += "\n"

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(md)

    def generate_comprehensive_table_report(self, comprehensive: Dict[str, Any],
                                            output_file: Path = None,
                                            max_width: int = 120) -> str:
        """Generate a matrix-style table with models as rows and tasks as columns.

        Args:
            comprehensive: Comprehensive report dictionary
            output_file: Optional output file path. If None, only returns the string.
            max_width: Maximum line width in characters (default: 82)

        Returns:
            The table as a string
        """
        task_ids = sorted(comprehensive.get("tasks", {}).keys())
        ranking = comprehensive.get("ranking", [])

        if not task_ids or not ranking:
            return "No results to display.\n"

        num_tasks = len(task_ids)
        model_names = [entry["model"] for entry in ranking]

        # Fixed layout: each data column is 5 chars wide ("100%" = 4 + 1 space)
        col_w = 5       # width per task column (includes leading space)
        ovr_w = 8       # width for Overall data column
        ovr_hdr = "Overall"

        # Model column sized to fit the longest model name
        model_w = max(max((len(m) for m in model_names), default=15), 15)

        # Use numbered task headers (T1, T2, ...) to save space
        task_headers = [f"T{i}" for i in range(1, num_tasks + 1)]

        # Build header
        header = f"{'Model':<{model_w}}"
        for th in task_headers:
            header += f"{th:>{col_w}}"
        header += f"{ovr_hdr:>{ovr_w}}"
        total_w = len(header)

        lines = []
        lines.append("Terraform Benchmark - Per-Task Pass Rate Matrix")
        lines.append(f"Generated: {comprehensive['timestamp']}")
        lines.append(f"Runs per task: up to 10 latest")
        lines.append("")
        lines.append("=" * total_w)
        lines.append(header)
        lines.append("-" * total_w)

        for entry in ranking:
            model = entry["model"]
            stats = comprehensive["models"][model]
            row = f"{model:<{model_w}}"
            for task_id in task_ids:
                task_data = stats.get("tasks", {}).get(task_id)
                if task_data is not None:
                    cell = f"{task_data['pass_rate']:.0f}%"
                else:
                    cell = "-"
                row += f"{cell:>{col_w}}"
            row += f"{stats['overall_pass_rate']:.0f}%".rjust(ovr_w)
            lines.append(row)

        lines.append("=" * total_w)

        # Legend mapping T1..TN to full task names
        lines.append("")
        lines.append("Tasks:")
        for i, task_id in enumerate(task_ids, 1):
            short = task_id.replace("task_", "") if task_id.startswith("task_") else task_id
            lines.append(f"  T{i:<3} {short}")

        lines.append(f"\nModels: {len(ranking)}  |  Tasks: {num_tasks}")
        lines.append("")

        table = "\n".join(lines)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(table)

        return table

