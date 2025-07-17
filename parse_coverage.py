#!/usr/bin/env python3
import json
import sys


def parse_coverage_report(report_file):
    """Parse coverage report and extract key metrics"""
    try:
        with open(report_file) as f:
            data = json.load(f)

        files = data.get("files", {})

        # Target modules
        targets = [
            "api_mcp_gateway.py",
            "tools/qdrant_vectorization_tool.py",
            "tools/document_ingestion_tool.py",
        ]

        print(f"Coverage Report Analysis from {report_file}")
        print("=" * 60)

        total_statements = 0
        total_covered = 0

        for target in targets:
            if target in files:
                file_data = files[target]
                summary = file_data.get("summary", {})

                covered = summary.get("covered_lines", 0)
                statements = summary.get("num_statements", 0)
                percent = summary.get("percent_covered", 0)
                missing = summary.get("missing_lines", 0)

                print(f"\n{target}:")
                print(f"  Coverage: {percent:.1f}%")
                print(f"  Statements: {statements}")
                print(f"  Covered: {covered}")
                print(f"  Missing: {missing}")

                total_statements += statements
                total_covered += covered
            else:
                print(f"\n{target}: NOT FOUND")

        # Overall coverage for these modules
        if total_statements > 0:
            overall_percent = (total_covered / total_statements) * 100
            print("\nOverall Coverage for Target Modules:")
            print(f"  Total Statements: {total_statements}")
            print(f"  Total Covered: {total_covered}")
            print(f"  Overall Coverage: {overall_percent:.1f}%")

        # Overall project coverage
        all_statements = 0
        all_covered = 0
        for file_path, file_data in files.items():
            summary = file_data.get("summary", {})
            all_statements += summary.get("num_statements", 0)
            all_covered += summary.get("covered_lines", 0)

        if all_statements > 0:
            project_percent = (all_covered / all_statements) * 100
            print("\nProject-wide Coverage:")
            print(f"  Total Statements: {all_statements}")
            print(f"  Total Covered: {all_covered}")
            print(f"  Project Coverage: {project_percent:.1f}%")

    except Exception as e:
        print(f"Error parsing coverage report: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        report_file = sys.argv[1]
    else:
        report_file = "ADK/agent_data/.coverage_cli140m1_final_report.json"

    parse_coverage_report(report_file)
