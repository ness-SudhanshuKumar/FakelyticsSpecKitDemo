"""Report formatting services for multiple output formats."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from src.api.models.schemas import CredibilityReport

logger = logging.getLogger(__name__)


class ReportFormatter:
    """Service for formatting credibility reports in multiple output formats."""

    def __init__(self):
        """Initialize report formatter."""
        pass

    def to_json(self, report: CredibilityReport, pretty: bool = True) -> str:
        """
        Format report as JSON.
        
        **Satisfies**: T-803 (JSON format - machine-readable)
        
        Args:
            report: Credibility report
            pretty: Whether to pretty-print JSON
            
        Returns:
            JSON string representation
        """
        try:
            report_dict = report.model_dump(mode="json")
            if pretty:
                return json.dumps(report_dict, indent=2, default=str)
            else:
                return json.dumps(report_dict, default=str)
        except Exception as e:
            logger.error(f"Error formatting report as JSON: {str(e)}")
            return "{}"

    def to_html(self, report: CredibilityReport) -> str:
        """
        Format report as HTML.
        
        **Satisfies**: T-803 (HTML format - human-readable)
        
        Args:
            report: Credibility report
            
        Returns:
            HTML string representation
        """
        try:
            # Determine credibility level based on score
            if report.overall_credibility_score >= 80:
                credibility_class = "highly-credible"
                credibility_label = "Highly Credible"
            elif report.overall_credibility_score >= 60:
                credibility_class = "credible"
                credibility_label = "Credible"
            elif report.overall_credibility_score >= 40:
                credibility_class = "neutral"
                credibility_label = "Neutral"
            elif report.overall_credibility_score >= 20:
                credibility_class = "low-credible"
                credibility_label = "Low Credibility"
            else:
                credibility_class = "not-credible"
                credibility_label = "Not Credible"

            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fakelytics Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .report {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .score-box {{
            display: inline-block;
            font-size: 48px;
            font-weight: bold;
            padding: 20px 30px;
            border-radius: 8px;
            margin-right: 20px;
            color: white;
        }}
        .score-box.highly-credible {{ background-color: #27ae60; }}
        .score-box.credible {{ background-color: #3498db; }}
        .score-box.neutral {{ background-color: #f39c12; }}
        .score-box.low-credible {{ background-color: #e67e22; }}
        .score-box.not-credible {{ background-color: #e74c3c; }}
        .credibility-label {{
            display: inline-block;
            font-size: 24px;
            font-weight: 600;
            vertical-align: middle;
        }}
        .url {{
            word-break: break-all;
            font-family: monospace;
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 14px;
        }}
        .summary {{
            background-color: #ecf0f1;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .findings {{
            margin-top: 30px;
        }}
        .finding {{
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .finding-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .finding-title {{
            font-weight: 600;
            font-size: 16px;
        }}
        .verdict {{
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            color: white;
        }}
        .verdict.supported {{ background-color: #27ae60; }}
        .verdict.disputed {{ background-color: #e74c3c; }}
        .verdict.unverifiable {{ background-color: #95a5a6; }}
        .confidence {{
            font-size: 14px;
            color: #666;
        }}
        .evidence {{
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 14px;
        }}
        .evidence-url {{
            color: #3498db;
            text-decoration: none;
        }}
        .evidence-url:hover {{
            text-decoration: underline;
        }}
        .footer {{
            border-top: 1px solid #ddd;
            padding-top: 20px;
            margin-top: 30px;
            font-size: 12px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="report">
        <div class="header">
            <h1>Fakelytics Credibility Report</h1>
            <div>
                <span class="score-box {credibility_class}">{report.overall_credibility_score}/100</span>
                <span class="credibility-label">{credibility_label}</span>
            </div>
            <div style="margin-top: 15px;">
                <strong>URL:</strong>
                <div class="url">{self._html_escape(report.url)}</div>
            </div>
        </div>

        <div class="summary">
            <strong>Summary:</strong><br>
            {self._html_escape(report.summary)}
        </div>

        <div class="findings">
            <h2>Analysis Results</h2>
"""

            # Add findings from each pipeline
            for pipeline_name in ["text", "image", "audio_video", "spam"]:
                pipeline_result = getattr(report.findings, pipeline_name, None)
                if pipeline_result and pipeline_result.findings:
                    html += f"<h3>{self._pipeline_name_display(pipeline_name)}</h3>\n"
                    html += f"<p><strong>Verdict:</strong> <span class=\"verdict {pipeline_result.verdict.lower()}\">{pipeline_result.verdict}</span></p>\n"
                    html += f"<p><strong>Confidence:</strong> {pipeline_result.confidence}%</p>\n"
                    
                    for finding in pipeline_result.findings:
                        html += f"""
                        <div class="finding">
                            <div class="finding-header">
                                <span class="finding-title">{self._html_escape(finding.summary)}</span>
                                <span class="verdict {finding.verdict.lower()}">{finding.verdict}</span>
                            </div>
                            <div class="confidence">Confidence: {finding.confidence}%</div>
"""
                        if finding.evidence:
                            html += '<div class="evidence"><strong>Evidence:</strong><ul>'
                            for evidence in finding.evidence:
                                html += f'<li><a href="{self._html_escape(evidence.url)}" class="evidence-url">{self._html_escape(evidence.title or evidence.url)}</a></li>'
                            html += '</ul></div>'
                        html += '</div>\n'

            html += f"""
        </div>

        <div class="footer">
            <p>Report ID: {report.request_id}</p>
            <p>Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p>Fakelytics &copy; 2026. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
            return html
            
        except Exception as e:
            logger.error(f"Error formatting report as HTML: {str(e)}", exc_info=True)
            return "<html><body><p>Error generating HTML report</p></body></html>"

    def to_text(self, report: CredibilityReport) -> str:
        """
        Format report as plain text.
        
        **Satisfies**: T-803 (Plain text format)
        
        Args:
            report: Credibility report
            
        Returns:
            Plain text string representation
        """
        try:
            text = "=" * 80 + "\n"
            text += "FAKELYTICS CREDIBILITY REPORT\n"
            text += "=" * 80 + "\n\n"
            
            text += f"Overall Score: {report.overall_credibility_score}/100\n"
            text += f"URL: {report.url}\n"
            text += f"Report ID: {report.request_id}\n"
            text += f"Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            
            text += "SUMMARY\n"
            text += "-" * 80 + "\n"
            text += report.summary + "\n\n"
            
            text += "ANALYSIS RESULTS\n"
            text += "-" * 80 + "\n"
            
            for pipeline_name in ["text", "image", "audio_video", "spam"]:
                pipeline_result = getattr(report.findings, pipeline_name, None)
                if pipeline_result and pipeline_result.findings:
                    text += f"\n{self._pipeline_name_display(pipeline_name).upper()}\n"
                    text += f"Verdict: {pipeline_result.verdict}\n"
                    text += f"Confidence: {pipeline_result.confidence}%\n"
                    
                    for i, finding in enumerate(pipeline_result.findings, 1):
                        text += f"\n  Finding {i}: {finding.summary}\n"
                        text += f"  Verdict: {finding.verdict}\n"
                        text += f"  Confidence: {finding.confidence}%\n"
                        
                        if finding.evidence:
                            text += "  Evidence:\n"
                            for evidence in finding.evidence:
                                text += f"    - {evidence.title or evidence.url}\n"
                                text += f"      URL: {evidence.url}\n"
            
            text += "\n" + "=" * 80 + "\n"
            text += "End of Report\n"
            text += "=" * 80 + "\n"
            
            return text
            
        except Exception as e:
            logger.error(f"Error formatting report as text: {str(e)}", exc_info=True)
            return "Error generating text report"

    @staticmethod
    def _html_escape(text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))

    @staticmethod
    def _pipeline_name_display(name: str) -> str:
        """Convert pipeline name to display format."""
        mapping = {
            "text": "Text Analysis",
            "image": "Image Analysis",
            "audio_video": "Audio/Video Analysis",
            "spam": "Spam & Source Detection"
        }
        return mapping.get(name, name.replace("_", " ").title())


# Global instance
report_formatter = ReportFormatter()
