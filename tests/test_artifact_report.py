"""Tests for the artifact HTML report renderer."""

from __future__ import annotations

import json
from pathlib import Path

from alphaforge.artifact_report import render_artifact_report


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "artifact_report"


class TestRenderArtifactReport:
    def test_renders_html_with_all_artifacts(self, tmp_path: Path) -> None:
        output = tmp_path / "report.html"
        result = render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)
        assert Path(result) == output
        html = output.read_text(encoding="utf-8")
        assert "Equity Curve" in html
        assert "Drawdown" in html
        assert "Trade Log" in html
        assert "Generated" in html
        assert "Metric Summary" in html

    def test_handles_missing_optional_files(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=empty_dir, output_path=output)
        html = output.read_text(encoding="utf-8")
        assert "Warnings" in html
        assert "metrics_summary.json is missing" in html
        assert "Generated" in html

    def test_renders_oap_report_json(self, tmp_path: Path) -> None:
        oap_report_path = FIXTURE_DIR / "oap_report.json"
        output = tmp_path / "oap_report.html"
        result = render_artifact_report(
            artifact_dir=FIXTURE_DIR,
            output_path=output,
            report_json_path=oap_report_path,
        )
        assert Path(result) == output
        html = output.read_text(encoding="utf-8")
        assert "OAP Real-Data Report" in html
        assert "Generated" in html

    def test_equity_curve_and_drawdown_charts_present(self, tmp_path: Path) -> None:
        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)
        html = output.read_text(encoding="utf-8")
        assert "Equity Curve" in html
        assert "Drawdown" in html

    def test_trade_log_table_present(self, tmp_path: Path) -> None:
        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)
        html = output.read_text(encoding="utf-8")
        assert "Trade Log" in html

    def test_no_warnings_when_all_files_present(self, tmp_path: Path) -> None:
        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)
        html = output.read_text(encoding="utf-8")
        assert "Warnings" not in html

    def test_output_path_default(self, tmp_path: Path) -> None:
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()
        (artifact_dir / "metrics_summary.json").write_text(
            json.dumps({"total_return": 0.1}), encoding="utf-8"
        )
        result = render_artifact_report(artifact_dir=artifact_dir)
        assert Path(result) == artifact_dir / "report.html"
        assert Path(result).exists()

    def test_html_contains_generated_timestamp(self, tmp_path: Path) -> None:
        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)
        html = output.read_text(encoding="utf-8")
        assert "Generated" in html

    def test_validation_summary_rendered(self, tmp_path: Path) -> None:
        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)
        html = output.read_text(encoding="utf-8")
        assert "Validation Summary" in html

    def test_walk_forward_summary_rendered(self, tmp_path: Path) -> None:
        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)
        html = output.read_text(encoding="utf-8")
        assert "Walk-Forward Summary" in html

    def test_permutation_summary_rendered(self, tmp_path: Path) -> None:
        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)
        html = output.read_text(encoding="utf-8")
        assert "Permutation Test Summary" in html

    def test_drawdown_chart_contains_negative_values(self, tmp_path: Path) -> None:
        import json
        import re

        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)

        html = output.read_text(encoding="utf-8")

        plots = list(re.finditer(r"Plotly\.newPlot", html))
        assert len(plots) >= 2, "Expected at least 2 charts"

        start = plots[1].start()
        next_plot = html.find("Plotly.newPlot", start + 1)
        end = next_plot if next_plot != -1 else html.find("</script>", start)
        section = html[start:end]

        trace_start = section.find("[{")
        trace_end = section.find("}]")
        assert trace_start != -1 and trace_end != -1, "Drawdown trace not found"

        trace_json = section[trace_start : trace_end + 2]
        trace = json.loads(trace_json)[0]

        y_data = trace["y"]

        assert isinstance(y_data, list)
        assert any(value < 0 for value in y_data)
        assert all(value <= 0 for value in y_data)

    def test_ranked_results_rendered(self, tmp_path: Path) -> None:
        output = tmp_path / "report.html"
        render_artifact_report(artifact_dir=FIXTURE_DIR, output_path=output)
        html = output.read_text(encoding="utf-8")
        assert "Ranked Results" in html

    def test_render_artifact_report_cli(self, tmp_path: Path) -> None:
        from alphaforge.cli import build_parser

        parser = build_parser()
        output = tmp_path / "report.html"
        args = parser.parse_args([
            "render-artifact-report",
            "--artifact-dir", str(FIXTURE_DIR),
            "--output", str(output),
        ])
        from alphaforge.artifact_report import render_artifact_report as func

        result = func(
            artifact_dir=args.artifact_dir,
            output_path=args.output,
            report_json_path=args.report_json,
        )
        assert Path(result) == output
        assert output.exists()
        html = output.read_text(encoding="utf-8")
        assert "Generated" in html
        assert "Equity Curve" in html

    def test_render_artifact_report_cli_with_oap_json(self, tmp_path: Path) -> None:
        from alphaforge.cli import build_parser

        parser = build_parser()
        output = tmp_path / "oap_report.html"
        oap_json = FIXTURE_DIR / "oap_report.json"
        args = parser.parse_args([
            "render-artifact-report",
            "--artifact-dir", str(FIXTURE_DIR),
            "--output", str(output),
            "--report-json", str(oap_json),
        ])
        from alphaforge.artifact_report import render_artifact_report as func

        result = func(
            artifact_dir=args.artifact_dir,
            output_path=args.output,
            report_json_path=args.report_json,
        )
        assert Path(result) == output
        html = output.read_text(encoding="utf-8")
        assert "OAP Real-Data Report" in html
