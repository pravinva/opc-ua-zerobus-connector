"""HTML/CSS/JavaScript templates for the web UI.

This module contains all the front-end templates separated from the backend logic.
"""

from __future__ import annotations


def get_head_html() -> str:
    """Return the HTML head section with meta tags and external resources."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Databricks OT Simulator - Professional Edition</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cdefs%3E%3ClinearGradient id='grad' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%23FF3621;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%23FF8A00;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='100' height='100' rx='20' fill='url(%23grad)'/%3E%3Cg fill='white'%3E%3Ccircle cx='30' cy='50' r='8'/%3E%3Ccircle cx='50' cy='30' r='8'/%3E%3Ccircle cx='50' cy='70' r='8'/%3E%3Ccircle cx='70' cy='50' r='8'/%3E%3Cline x1='30' y1='50' x2='50' y2='30' stroke='white' stroke-width='3'/%3E%3Cline x1='30' y1='50' x2='50' y2='70' stroke='white' stroke-width='3'/%3E%3Cline x1='50' y1='30' x2='70' y2='50' stroke='white' stroke-width='3'/%3E%3Cline x1='50' y1='70' x2='70' y2='50' stroke='white' stroke-width='3'/%3E%3C/g%3E%3C/svg%3E">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/fft.js@4.0.3/lib/fft.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/plotly.js@2.27.0/dist/plotly.min.js"></script>"""


def get_styles_html() -> str:
    """Return the CSS styles for the web UI."""
    return """    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #F7F8FA;
            color: #2E3036;
            min-height: 100vh;
            padding: 24px;
            overflow-x: hidden;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            background: white;
            border: 1px solid #E3E5E8;
            border-radius: 8px;
            padding: 32px;
            margin-bottom: 32px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .logo-section {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 16px;
        }

        .databricks-logo {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #FF3621 0%, #FF6B58 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 24px;
            color: white;
            box-shadow: 0 4px 16px rgba(255, 54, 33, 0.4);
        }

        h1 {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, #FF3621 0%, #00A9E0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .subtitle {
            color: #6B7280;
            margin-top: 8px;
            font-size: 14px;
        }

        /* Main Grid */
        .main-grid {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }

        /* Sidebar */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .card {
            background: white;
            border: 1px solid #E3E5E8;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .protocol-selector {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .protocol-item {
            display: flex;
            flex-direction: column;
            background: #F9FAFB;
            border: 1px solid #E3E5E8;
            border-radius: 8px;
            transition: all 0.3s;
            width: 100%;
        }

        .protocol-item:hover {
            background: #F3F4F6;
            border-color: #D1D5DB;
        }

        .protocol-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 24px;
            min-height: 70px;
            gap: 24px;
            flex-wrap: nowrap;
        }

        .protocol-config-panel {
            display: none;
            padding: 0 24px 20px 24px;
            border-top: 1px solid #E3E5E8;
            background: white;
        }

        .protocol-config-panel.expanded {
            display: block;
        }

        .config-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }

        .config-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .config-label {
            font-size: 12px;
            font-weight: 600;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .config-input {
            padding: 10px 12px;
            background: #F9FAFB;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            font-size: 14px;
            color: #2E3036;
            font-family: 'Inter', sans-serif;
            transition: all 0.3s;
        }

        .config-input:focus {
            outline: none;
            border-color: #FF3621;
            background: white;
            box-shadow: 0 0 0 2px rgba(255, 54, 33, 0.1);
        }

        .config-input::placeholder {
            color: #9CA3AF;
        }

        .config-toggle {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            padding: 8px 12px;
            background: white;
            border: 1px solid #E3E5E8;
            border-radius: 6px;
            transition: all 0.3s;
            font-size: 13px;
            color: #6B7280;
            font-weight: 500;
        }

        .config-toggle:hover {
            background: #F9FAFB;
            border-color: #D1D5DB;
        }

        .config-toggle-icon {
            transition: transform 0.3s;
        }

        .config-toggle-icon.expanded {
            transform: rotate(180deg);
        }

        .config-actions {
            display: flex;
            gap: 8px;
            margin-top: 16px;
        }

        .btn-save {
            padding: 10px 20px;
            background: #FF3621;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-save:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(255, 54, 33, 0.3);
        }

        .btn-test {
            padding: 10px 20px;
            background: white;
            color: #6B7280;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-test:hover {
            background: #F9FAFB;
            border-color: #9CA3AF;
        }

        .btn-start-zerobus {
            padding: 10px 20px;
            background: #10B981;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s;
        }

        .btn-start-zerobus:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }

        .btn-start-zerobus:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-stop-zerobus {
            padding: 10px 20px;
            background: #EF4444;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s;
        }

        .btn-stop-zerobus:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        }

        .btn-stop-zerobus:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .protocol-badge {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #9CA3AF;
            transition: all 0.3s;
        }

        .protocol-badge.running {
            background: #10B981;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
        }

        .protocol-name {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 13px;
            letter-spacing: 0.5px;
            white-space: nowrap;
            flex-shrink: 0;
            min-width: 80px;
        }

        .protocol-endpoint {
            font-size: 11px;
            color: #6B7280;
            font-family: 'Monaco', 'Courier New', monospace;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex: 1 1 auto;
            min-width: 0;
        }

        .protocol-endpoint a {
            color: #00A9E0;
            text-decoration: none;
            transition: all 0.2s;
        }

        .protocol-endpoint a:hover {
            color: #FF3621;
            text-decoration: underline;
        }

        .protocol-controls {
            display: flex;
            gap: 12px;
            flex-shrink: 0;
            align-self: center;
            flex-wrap: nowrap;
            margin-left: auto;
        }

        .btn {
            padding: 8px 16px;
            border-radius: 6px;
            border: none;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            min-width: 70px;
            white-space: nowrap;
        }

        .btn-start {
            background: #10B981;
            color: white;
        }

        .btn-start:hover {
            background: #059669;
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
        }

        .btn-stop {
            background: #FEE2E2;
            color: #DC2626;
            border: 1px solid #FCA5A5;
        }

        .btn-stop:hover {
            background: #FEF2F2;
        }

        /* Chart Section */
        .chart-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 24px;
        }

        .chart-card {
            background: white;
            border: 1px solid #E3E5E8;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .chart-title {
            font-size: 14px;
            font-weight: 600;
            color: #6B7280;
            font-family: 'Monaco', 'Courier New', monospace;
        }

        .live-value {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #FF3621 0%, #00A9E0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .chart-container {
            position: relative;
            height: 300px;
        }

        /* Advanced Visualization Buttons */
        .btn-fft, .btn-spectrogram, .btn-spc {
            padding: 6px 12px;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            margin-left: 8px;
        }

        .btn-fft {
            background: #00A9E0;
        }

        .btn-fft:hover {
            background: #0088B8;
            transform: translateY(-1px);
        }

        .btn-fft.active {
            background: #FF3621;
        }

        .btn-spectrogram {
            background: #8B5CF6;
        }

        .btn-spectrogram:hover {
            background: #7C3AED;
            transform: translateY(-1px);
        }

        .btn-spectrogram.active {
            background: #FF3621;
        }

        .btn-spc {
            background: #059669;
        }

        .btn-spc:hover {
            background: #047857;
            transform: translateY(-1px);
        }

        .btn-spc.active {
            background: #FF3621;
        }

        .chart-buttons {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        /* Natural Language Chat Button */
        .nlp-chat-button {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: linear-gradient(135deg, #FF3621 0%, #FF6B58 100%);
            color: white;
            border: none;
            padding: 16px 24px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 8px 32px rgba(255, 54, 33, 0.4);
            transition: all 0.3s;
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nlp-chat-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(255, 54, 33, 0.6);
        }

        /* Chat Panel */
        .nlp-chat-panel {
            position: fixed;
            top: 0;
            right: 0;
            width: 450px;
            height: 100vh;
            background: white;
            border-left: 1px solid #E3E5E8;
            box-shadow: -4px 0 16px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 2000;
        }

        .nlp-chat-panel.hidden {
            transform: translateX(100%);
        }

        .chat-header {
            padding: 24px;
            border-bottom: 1px solid #E3E5E8;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .chat-header h3 {
            font-size: 18px;
            font-weight: 600;
            color: #2E3036;
        }

        .chat-close {
            background: none;
            border: none;
            color: #6B7280;
            font-size: 28px;
            cursor: pointer;
            transition: color 0.3s;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .chat-close:hover {
            color: #2E3036;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .chat-messages::-webkit-scrollbar {
            width: 8px;
        }

        .chat-messages::-webkit-scrollbar-track {
            background: #F3F4F6;
        }

        .chat-messages::-webkit-scrollbar-thumb {
            background: #D1D5DB;
            border-radius: 4px;
        }

        .message {
            display: flex;
            gap: 12px;
            animation: fadeIn 0.3s ease-out;
        }

        .message.user {
            justify-content: flex-end;
        }

        .message-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
        }

        .message.user .message-avatar {
            background: linear-gradient(135deg, #00A9E0 0%, #0088C7 100%);
            order: 2;
        }

        .message.agent .message-avatar {
            background: linear-gradient(135deg, #FF3621 0%, #FF6B58 100%);
        }

        .message-content {
            max-width: 70%;
        }

        .message-bubble {
            padding: 12px 16px;
            border-radius: 16px;
            font-size: 14px;
            line-height: 1.5;
        }

        .message.user .message-bubble {
            background: linear-gradient(135deg, #00A9E0 0%, #0088C7 100%);
            color: white;
            border-radius: 16px 16px 4px 16px;
        }

        .message.agent .message-bubble {
            background: #F3F4F6;
            border: 1px solid #E3E5E8;
            color: #2E3036;
            border-radius: 16px 16px 16px 4px;
        }

        .message-reasoning {
            font-size: 12px;
            color: #6B7280;
            margin-top: 4px;
            font-style: italic;
            padding: 8px 12px;
            background: #FEF2F2;
            border-radius: 8px;
            border-left: 2px solid #FF3621;
        }

        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px 16px 16px 4px;
            width: fit-content;
        }

        .typing-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #A0A4A8;
            animation: typing 1.4s infinite;
        }

        .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
                opacity: 0.7;
            }
            30% {
                transform: translateY(-10px);
                opacity: 1;
            }
        }

        .chat-input-container {
            padding: 24px;
            border-top: 1px solid #E3E5E8;
            display: flex;
            gap: 12px;
        }

        .chat-input {
            flex: 1;
            padding: 12px 16px;
            background: white;
            border: 1px solid #D1D5DB;
            border-radius: 8px;
            color: #2E3036;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
            transition: all 0.3s;
        }

        .chat-input:focus {
            outline: none;
            border-color: #FF3621;
            box-shadow: 0 0 0 2px rgba(255, 54, 33, 0.1);
        }

        .chat-input::placeholder {
            color: #9CA3AF;
        }

        .chat-send {
            padding: 12px 24px;
            background: #FF3621;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .chat-send:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 16px rgba(255, 54, 33, 0.4);
        }

        .chat-send:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* Sensor Browser */
        .sensor-browser {
            max-height: 500px;
            overflow-y: auto;
        }

        .sensor-browser::-webkit-scrollbar {
            width: 8px;
        }

        .sensor-browser::-webkit-scrollbar-track {
            background: #F3F4F6;
        }

        .sensor-browser::-webkit-scrollbar-thumb {
            background: #D1D5DB;
            border-radius: 4px;
        }

        .industry-accordion {
            margin-bottom: 8px;
            border: 1px solid #E3E5E8;
            border-radius: 8px;
            overflow: hidden;
            background: white;
        }

        .industry-header {
            padding: 12px 16px;
            background: linear-gradient(90deg, #F9FAFB 0%, #F3F4F6 100%);
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
            border-bottom: 1px solid transparent;
        }

        .industry-header:hover {
            background: linear-gradient(90deg, #F3F4F6 0%, #E5E7EB 100%);
        }

        .industry-header.active {
            background: linear-gradient(90deg, #DBEAFE 0%, #BFDBFE 100%);
            border-bottom-color: #93C5FD;
        }

        .industry-header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .industry-title {
            font-size: 13px;
            font-weight: 600;
            color: #1F2937;
        }

        .industry-count {
            font-size: 11px;
            color: #6B7280;
            background: #F9FAFB;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 500;
        }

        .industry-chevron {
            font-size: 14px;
            color: #6B7280;
            transition: transform 0.2s;
        }

        .industry-chevron.expanded {
            transform: rotate(90deg);
        }

        .industry-sensors {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }

        .industry-sensors.expanded {
            max-height: 2000px;
            transition: max-height 0.5s ease-in;
        }

        .sensor-item {
            padding: 10px 16px;
            background: white;
            border-bottom: 1px solid #F3F4F6;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .sensor-item:hover {
            background: #F9FAFB;
            border-left: 3px solid #FF3621;
            padding-left: 13px;
        }

        .sensor-item.selected {
            background: #DBEAFE;
            border-left: 4px solid #00A9E0;
            padding-left: 12px;
        }

        .sensor-item.selected:hover {
            background: #BFDBFE;
        }

        .sensor-item:last-child {
            border-bottom: none;
        }

        .sensor-info {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .sensor-name {
            font-size: 12px;
            font-family: 'Monaco', 'Courier New', monospace;
            color: #1F2937;
            font-weight: 500;
        }

        .sensor-meta {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .sensor-type {
            font-size: 10px;
            color: #6B7280;
        }

        .protocol-badges {
            display: flex;
            gap: 4px;
        }

        .protocol-badge-mini {
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .protocol-badge-mini.opcua {
            background: #DBEAFE;
            color: #1E40AF;
        }

        .protocol-badge-mini.mqtt {
            background: #D1FAE5;
            color: #065F46;
        }

        .protocol-badge-mini.modbus {
            background: #FED7AA;
            color: #9A3412;
        }

        .sensor-add {
            font-size: 20px;
            color: #A0A4A8;
            transition: all 0.2s;
        }

        .sensor-item:hover .sensor-add {
            color: #FF3621;
            transform: scale(1.2);
        }

        /* OPC-UA Browser Panel */
        .opcua-browser-button {
            position: fixed;
            bottom: 90px;
            right: 24px;
            background: linear-gradient(135deg, #00A9E0 0%, #0088C7 100%);
            color: white;
            border: none;
            padding: 16px 24px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 8px 32px rgba(0, 169, 224, 0.4);
            transition: all 0.3s;
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .opcua-browser-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 169, 224, 0.6);
        }

        .opcua-browser-panel {
            position: fixed;
            top: 0;
            right: 0;
            width: 550px;
            height: 100vh;
            background: white;
            border-left: 1px solid #E3E5E8;
            box-shadow: -4px 0 16px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 2000;
        }

        .opcua-browser-panel.hidden {
            transform: translateX(100%);
        }

        .opcua-browser-header {
            padding: 24px;
            border-bottom: 1px solid #E3E5E8;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(135deg, #1B3139 0%, #2E4A57 100%);
            color: white;
        }

        .opcua-browser-header h3 {
            font-size: 18px;
            font-weight: 600;
            margin: 0;
        }

        .opcua-browser-close {
            background: none;
            border: none;
            color: white;
            font-size: 28px;
            cursor: pointer;
            transition: color 0.3s;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .opcua-browser-close:hover {
            color: #00A9E0;
        }

        .opcua-search-container {
            padding: 16px;
            border-bottom: 1px solid #E3E5E8;
            background: #F9FAFB;
        }

        .opcua-search-input {
            width: 100%;
            padding: 10px 16px;
            background: white;
            border: 1px solid #D1D5DB;
            border-radius: 8px;
            color: #2E3036;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
            transition: all 0.3s;
        }

        .opcua-search-input:focus {
            outline: none;
            border-color: #00A9E0;
            box-shadow: 0 0 0 2px rgba(0, 169, 224, 0.1);
        }

        .opcua-search-input::placeholder {
            color: #9CA3AF;
        }

        .opcua-tree-container {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }

        .opcua-tree-container::-webkit-scrollbar {
            width: 8px;
        }

        .opcua-tree-container::-webkit-scrollbar-track {
            background: #F3F4F6;
        }

        .opcua-tree-container::-webkit-scrollbar-thumb {
            background: #D1D5DB;
            border-radius: 4px;
        }

        .tree-node {
            margin-bottom: 4px;
        }

        .tree-node-header {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            user-select: none;
        }

        .tree-node-header:hover {
            background: #F3F4F6;
        }

        .tree-node-header.active {
            background: #DBEAFE;
        }

        .tree-chevron {
            font-size: 12px;
            color: #6B7280;
            transition: transform 0.2s;
            width: 16px;
            display: inline-block;
        }

        .tree-chevron.expanded {
            transform: rotate(90deg);
        }

        .tree-chevron.leaf {
            visibility: hidden;
        }

        .tree-icon {
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }

        .tree-label {
            flex: 1;
            font-size: 13px;
            color: #1F2937;
            font-weight: 500;
        }

        .tree-value {
            font-size: 12px;
            font-family: 'Monaco', 'Courier New', monospace;
            color: #00A9E0;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .tree-value.updated {
            color: #FF3621;
            transform: scale(1.1);
            animation: valueFlash 0.5s ease;
        }

        @keyframes valueFlash {
            0% {
                background: rgba(255, 54, 33, 0.2);
                border-radius: 4px;
                padding: 2px 4px;
            }
            50% {
                background: rgba(255, 54, 33, 0.4);
            }
            100% {
                background: transparent;
                padding: 0;
            }
        }

        .tree-unit {
            font-size: 11px;
            color: #6B7280;
            margin-left: 4px;
        }

        .tree-quality {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            margin-left: 8px;
        }

        .tree-quality.good {
            background: #D1FAE5;
            color: #065F46;
        }

        .tree-quality.uncertain {
            background: #FEF3C7;
            color: #92400E;
        }

        .tree-quality.bad {
            background: #FEE2E2;
            color: #991B1B;
        }

        .tree-quality.forced {
            background: #DBEAFE;
            color: #1E40AF;
        }

        .tree-children {
            margin-left: 24px;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }

        .tree-children.expanded {
            max-height: 10000px;
            transition: max-height 0.5s ease-in;
        }

        .tree-properties {
            margin-left: 44px;
            margin-top: 8px;
            padding: 12px;
            background: #F9FAFB;
            border-radius: 6px;
            border-left: 3px solid #00A9E0;
        }

        .tree-property {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            font-size: 12px;
        }

        .tree-property-name {
            color: #6B7280;
            font-weight: 500;
        }

        .tree-property-value {
            color: #1F2937;
            font-family: 'Monaco', 'Courier New', monospace;
            font-weight: 600;
        }

        /* Responsive */
        @media (max-width: 1200px) {
            .main-grid {
                grid-template-columns: 1fr;
            }

            .nlp-chat-panel, .opcua-browser-panel {
                width: 100%;
            }

            .chart-section {
                grid-template-columns: 1fr;
            }
        }

        /* Sensor Selection Styles */
        .btn-select-sensors {
            padding: 10px 20px;
            background: linear-gradient(135deg, #00A8E1 0%, #0088B8 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .btn-select-sensors:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 168, 225, 0.3);
        }

        .sensor-summary {
            margin-top: 8px;
            padding: 8px 12px;
            background: #F3F4F6;
            border-radius: 6px;
            font-size: 12px;
            color: #6B7280;
        }

        /* Sensor Selector Modal */
        .sensor-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            z-index: 10000;
            justify-content: center;
            align-items: center;
        }

        .sensor-modal.active {
            display: flex;
        }

        .sensor-modal-content {
            background: white;
            border-radius: 12px;
            width: 90%;
            max-width: 1200px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .sensor-modal-header {
            padding: 24px;
            border-bottom: 1px solid #E5E7EB;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .sensor-modal-title {
            font-size: 20px;
            font-weight: 700;
            color: #1B3139;
        }

        .sensor-modal-close {
            background: none;
            border: none;
            font-size: 24px;
            color: #6B7280;
            cursor: pointer;
            padding: 4px 8px;
            line-height: 1;
        }

        .sensor-modal-close:hover {
            color: #FF3621;
        }

        .sensor-modal-body {
            padding: 24px;
            overflow-y: auto;
            flex: 1;
        }

        .sensor-filter-section {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }

        .sensor-filter-group {
            background: #F9FAFB;
            padding: 16px;
            border-radius: 8px;
        }

        .sensor-filter-label {
            font-size: 12px;
            font-weight: 600;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            display: block;
        }

        .sensor-filter-options {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 200px;
            overflow-y: auto;
        }

        .sensor-filter-option {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px;
            cursor: pointer;
        }

        .sensor-filter-option input[type="checkbox"] {
            width: 16px;
            height: 16px;
            cursor: pointer;
        }

        .sensor-filter-option label {
            font-size: 13px;
            color: #374151;
            cursor: pointer;
            flex: 1;
        }

        .sensor-list-section {
            background: #F9FAFB;
            border-radius: 8px;
            padding: 16px;
        }

        .sensor-list-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .sensor-list-title {
            font-size: 14px;
            font-weight: 600;
            color: #374151;
        }

        .sensor-list-actions {
            display: flex;
            gap: 12px;
        }

        .sensor-list-btn {
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 600;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .sensor-list-btn.select-all {
            background: #00A8E1;
            color: white;
        }

        .sensor-list-btn.select-all:hover {
            background: #0088B8;
        }

        .sensor-list-btn.clear-all {
            background: #E5E7EB;
            color: #374151;
        }

        .sensor-list-btn.clear-all:hover {
            background: #D1D5DB;
        }

        .sensor-items-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 8px;
            max-height: 300px;
            overflow-y: auto;
            padding: 8px;
            background: white;
            border-radius: 6px;
        }

        .sensor-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: #F9FAFB;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .sensor-item:hover {
            background: #F3F4F6;
        }

        .sensor-item input[type="checkbox"] {
            width: 16px;
            height: 16px;
            cursor: pointer;
        }

        .sensor-item-label {
            font-size: 12px;
            color: #374151;
            cursor: pointer;
            flex: 1;
        }

        .sensor-item-badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            background: #E5E7EB;
            color: #6B7280;
        }

        .sensor-modal-footer {
            padding: 24px;
            border-top: 1px solid #E5E7EB;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .sensor-selection-count {
            font-size: 14px;
            color: #6B7280;
        }

        .sensor-modal-actions {
            display: flex;
            gap: 12px;
        }

        .sensor-modal-btn {
            padding: 10px 24px;
            font-size: 14px;
            font-weight: 600;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .sensor-modal-btn.cancel {
            background: #E5E7EB;
            color: #374151;
        }

        .sensor-modal-btn.cancel:hover {
            background: #D1D5DB;
        }

        .sensor-modal-btn.apply {
            background: #FF3621;
            color: white;
        }

        .sensor-modal-btn.apply:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 54, 33, 0.3);
        }

        /* Diagnostics panel styles */
        .diagnostics-panel {
            margin-top: 15px;
            padding: 15px;
            border-radius: 8px;
            min-height: 60px;
            font-size: 14px;
            line-height: 1.6;
        }

        .diagnostics-panel .success {
            background: #D1FAE5;
            color: #065F46;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #10B981;
        }

        .diagnostics-panel .error {
            background: #FEE2E2;
            color: #991B1B;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #EF4444;
        }

        .diagnostics-panel .info {
            background: #DBEAFE;
            color: #1E40AF;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #3B82F6;
        }

        .diagnostics-panel small {
            display: block;
            margin-top: 8px;
            font-size: 12px;
            opacity: 0.8;
        }
    </style>
</head>"""


def get_body_html() -> str:
    """Return the HTML body structure."""
    return """<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo-section">
                <div class="databricks-logo">D</div>
                <div style="flex: 1;">
                    <h1>OT Data Simulator</h1>
                    <div class="subtitle">Real-Time Visualization • Natural Language AI • W3C WoT Discovery • ZeroBus Streaming</div>
                </div>
                <a href="/wot/browser" style="padding: 12px 24px; background: linear-gradient(135deg, #00A9E0 0%, #0080B3 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(0, 169, 224, 0.3); transition: all 0.3s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(0, 169, 224, 0.4)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(0, 169, 224, 0.3)'">
                    <span style="font-size: 18px;">🌐</span>
                    <span>WoT Browser</span>
                    <span style="font-size: 10px; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 12px;">379 sensors</span>
                </a>
            </div>
        </div>

        <!-- Protocol Control (Full Width) -->
        <div class="card" style="margin-bottom: 24px;">
            <div class="card-title">📡 Protocol Simulators</div>
            <div class="protocol-selector">
                <!-- OPC-UA Protocol -->
                <div class="protocol-item">
                    <div class="protocol-header">
                        <div class="protocol-badge" id="status-opcua"></div>
                        <span class="protocol-name">OPC-UA</span>
                        <div class="protocol-endpoint">
                            opc.tcp://0.0.0.0:4840/ot-simulator/server/
                        </div>
                        <div class="protocol-controls">
                            <button class="btn btn-start" id="start-opcua" onclick="startProtocol('opcua')">Start</button>
                            <button class="btn btn-stop" id="stop-opcua" onclick="stopProtocol('opcua')">Stop</button>
                            <button class="config-toggle" onclick="toggleConfig('opcua')">
                                <span>Zero-Bus Config</span>
                                <span class="config-toggle-icon" id="toggle-opcua">▼</span>
                            </button>
                        </div>
                    </div>
                    <div class="protocol-config-panel" id="config-opcua">
                        <div class="config-row">
                            <div class="config-field">
                                <label class="config-label">Workspace Host</label>
                                <input type="text" class="config-input" id="opcua-workspace"
                                       placeholder="https://your-workspace.cloud.databricks.com" />
                            </div>
                            <div class="config-field">
                                <label class="config-label">Zero-Bus Endpoint</label>
                                <input type="text" class="config-input" id="opcua-zerobus"
                                       placeholder="xxxxx.zerobus.region.cloud.databricks.com" />
                            </div>
                        </div>
                        <div class="config-row">
                            <div class="config-field">
                                <label class="config-label">OAuth Client ID</label>
                                <input type="text" class="config-input" id="opcua-client-id"
                                       placeholder="Enter OAuth Client ID" />
                            </div>
                            <div class="config-field">
                                <label class="config-label">OAuth Client Secret</label>
                                <input type="password" class="config-input" id="opcua-client-secret"
                                       placeholder="Enter OAuth Client Secret" />
                            </div>
                        </div>
                        <div class="config-row">
                            <div class="config-field" style="flex: 2;">
                                <label class="config-label">Target Table (catalog.schema.table)</label>
                                <input type="text" class="config-input" id="opcua-target"
                                       placeholder="opcua.scada_data.opcua_events_bronze" />
                            </div>
                        </div>
                        <div class="config-row">
                            <div class="config-field" style="flex: 2;">
                                <label class="config-label">Select Sensors/Tags 📊</label>
                                <button class="btn-select-sensors" onclick="openSensorSelector('opcua')">🏷️ Choose Sensors</button>
                                <div id="opcua-sensor-summary" class="sensor-summary">All sensors selected (379 total)</div>
                            </div>
                        </div>
                        <div class="config-actions">
                            <button class="btn-save" onclick="saveZeroBusConfig('opcua')">💾 Save Configuration</button>
                            <button class="btn-test" onclick="testZeroBusConnection('opcua')">🔌 Test Connection</button>
                            <button class="btn-start-zerobus" id="opcua-zerobus-btn" onclick="startZeroBusService('opcua')">▶️ Start Streaming</button>
                        </div>
                        <div id="opcua-diagnostics" class="diagnostics-panel"></div>
                    </div>
                </div>

                <!-- MQTT Protocol -->
                <div class="protocol-item">
                    <div class="protocol-header">
                        <div class="protocol-badge" id="status-mqtt"></div>
                        <span class="protocol-name">MQTT</span>
                        <div class="protocol-endpoint">
                            broker: localhost:1883
                        </div>
                        <div class="protocol-controls">
                            <button class="btn btn-start" id="start-mqtt" onclick="startProtocol('mqtt')">Start</button>
                            <button class="btn btn-stop" id="stop-mqtt" onclick="stopProtocol('mqtt')">Stop</button>
                            <button class="config-toggle" onclick="toggleConfig('mqtt')">
                                <span>Zero-Bus Config</span>
                                <span class="config-toggle-icon" id="toggle-mqtt">▼</span>
                            </button>
                        </div>
                    </div>
                    <div class="protocol-config-panel" id="config-mqtt">
                        <div class="config-row">
                            <div class="config-field">
                                <label class="config-label">Workspace Host</label>
                                <input type="text" class="config-input" id="mqtt-workspace"
                                       placeholder="https://your-workspace.cloud.databricks.com" />
                            </div>
                            <div class="config-field">
                                <label class="config-label">Zero-Bus Endpoint</label>
                                <input type="text" class="config-input" id="mqtt-zerobus"
                                       placeholder="xxxxx.zerobus.region.cloud.databricks.com" />
                            </div>
                        </div>
                        <div class="config-row">
                            <div class="config-field">
                                <label class="config-label">OAuth Client ID</label>
                                <input type="text" class="config-input" id="mqtt-client-id"
                                       placeholder="Enter OAuth Client ID" />
                            </div>
                            <div class="config-field">
                                <label class="config-label">OAuth Client Secret</label>
                                <input type="password" class="config-input" id="mqtt-client-secret"
                                       placeholder="Enter OAuth Client Secret" />
                            </div>
                        </div>
                        <div class="config-row">
                            <div class="config-field" style="flex: 2;">
                                <label class="config-label">Target Table (catalog.schema.table)</label>
                                <input type="text" class="config-input" id="mqtt-target"
                                       placeholder="mqtt.scada_data.mqtt_events_bronze" />
                            </div>
                        </div>
                        <div class="config-row">
                            <div class="config-field" style="flex: 2;">
                                <label class="config-label">Select Sensors/Tags 📊</label>
                                <button class="btn-select-sensors" onclick="openSensorSelector('mqtt')">🏷️ Choose Sensors</button>
                                <div id="mqtt-sensor-summary" class="sensor-summary">All sensors selected (379 total)</div>
                            </div>
                        </div>
                        <div class="config-actions">
                            <button class="btn-save" onclick="saveZeroBusConfig('mqtt')">💾 Save Configuration</button>
                            <button class="btn-test" onclick="testZeroBusConnection('mqtt')">🔌 Test Connection</button>
                            <button class="btn-start-zerobus" id="mqtt-zerobus-btn" onclick="startZeroBusService('mqtt')">▶️ Start Streaming</button>
                        </div>
                        <div id="mqtt-diagnostics" class="diagnostics-panel"></div>
                    </div>
                </div>

                <!-- Modbus Protocol -->
                <div class="protocol-item">
                    <div class="protocol-header">
                        <div class="protocol-badge" id="status-modbus"></div>
                        <span class="protocol-name">Modbus</span>
                        <div class="protocol-endpoint">
                            tcp://0.0.0.0:5020
                        </div>
                        <div class="protocol-controls">
                            <button class="btn btn-start" id="start-modbus" onclick="startProtocol('modbus')">Start</button>
                            <button class="btn btn-stop" id="stop-modbus" onclick="stopProtocol('modbus')">Stop</button>
                            <button class="config-toggle" onclick="toggleConfig('modbus')">
                                <span>Zero-Bus Config</span>
                                <span class="config-toggle-icon" id="toggle-modbus">▼</span>
                            </button>
                        </div>
                    </div>
                    <div class="protocol-config-panel" id="config-modbus">
                        <div class="config-row">
                            <div class="config-field">
                                <label class="config-label">Workspace Host</label>
                                <input type="text" class="config-input" id="modbus-workspace"
                                       placeholder="https://your-workspace.cloud.databricks.com" />
                            </div>
                            <div class="config-field">
                                <label class="config-label">Zero-Bus Endpoint</label>
                                <input type="text" class="config-input" id="modbus-zerobus"
                                       placeholder="xxxxx.zerobus.region.cloud.databricks.com" />
                            </div>
                        </div>
                        <div class="config-row">
                            <div class="config-field">
                                <label class="config-label">OAuth Client ID</label>
                                <input type="text" class="config-input" id="modbus-client-id"
                                       placeholder="Enter OAuth Client ID" />
                            </div>
                            <div class="config-field">
                                <label class="config-label">OAuth Client Secret</label>
                                <input type="password" class="config-input" id="modbus-client-secret"
                                       placeholder="Enter OAuth Client Secret" />
                            </div>
                        </div>
                        <div class="config-row">
                            <div class="config-field" style="flex: 2;">
                                <label class="config-label">Target Table (catalog.schema.table)</label>
                                <input type="text" class="config-input" id="modbus-target"
                                       placeholder="modbus.scada_data.modbus_events_bronze" />
                            </div>
                        </div>
                        <div class="config-row">
                            <div class="config-field" style="flex: 2;">
                                <label class="config-label">Select Sensors/Tags 📊</label>
                                <button class="btn-select-sensors" onclick="openSensorSelector('modbus')">🏷️ Choose Sensors</button>
                                <div id="modbus-sensor-summary" class="sensor-summary">All sensors selected (379 total)</div>
                            </div>
                        </div>
                        <div class="config-actions">
                            <button class="btn-save" onclick="saveZeroBusConfig('modbus')">💾 Save Configuration</button>
                            <button class="btn-test" onclick="testZeroBusConnection('modbus')">🔌 Test Connection</button>
                            <button class="btn-start-zerobus" id="modbus-zerobus-btn" onclick="startZeroBusService('modbus')">▶️ Start Streaming</button>
                        </div>
                        <div id="modbus-diagnostics" class="diagnostics-panel"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Grid -->
        <div class="main-grid">
            <!-- Sidebar -->
            <div class="sidebar">
                <!-- Sensor Browser -->
                <div class="card">
                    <div class="card-title">🔍 Add Sensors to Chart</div>
                    <div class="sensor-browser" id="sensor-browser">
                        <!-- Populated dynamically -->
                    </div>
                </div>
            </div>

            <!-- Chart Section -->
            <div class="chart-section" id="chart-section">
                <!-- Charts added dynamically -->
            </div>
        </div>
    </div>

    <!-- Operations AI Assistant Button -->
    <button class="nlp-chat-button" id="nlp-chat-toggle">
        🤖 Operations AI Assistant
    </button>

    <!-- Chat Panel -->
    <div class="nlp-chat-panel hidden" id="nlp-chat-panel">
        <div class="chat-header">
            <h3>Operations AI Assistant</h3>
            <button class="chat-close" id="chat-close">×</button>
        </div>

        <div class="chat-messages" id="chat-messages">
            <div class="message agent">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <div class="message-bubble">
                        <strong>Operations AI Assistant</strong><br>
                        I understand commands in plain English. Here are examples:<br><br>

                        <strong>Protocol Control:</strong><br>
                        • "Start opcua" or "Start the OPC-UA simulator"<br>
                        • "Stop mqtt" or "Stop MQTT publishing"<br>
                        • "What's the status of all simulators?"<br><br>

                        <strong>Sensor Information:</strong><br>
                        • "Show me all sensors in mining"<br>
                        • "List utilities sensors"<br>
                        • "What sensors are available?"<br><br>

                        <strong>Fault Injection:</strong><br>
                        • "Inject fault into mining/crusher_1_motor_power for 60 seconds"<br>
                        • "Break the conveyor belt sensor for 30 seconds"<br><br>

                        <strong>General Questions:</strong><br>
                        • "How many sensors are running?"<br>
                        • "Show me the manufacturing sensors"
                    </div>
                </div>
            </div>
        </div>

        <div class="chat-input-container">
            <input
                type="text"
                class="chat-input"
                id="chat-input"
                placeholder="Type your command... (e.g., 'start opcua')"
                autocomplete="off"
            />
            <button class="chat-send" id="chat-send">Send</button>
        </div>
    </div>

    <!-- OPC-UA Browser Button -->
    <button class="opcua-browser-button" id="opcua-browser-toggle">
        📡 Browse OPC-UA
    </button>

    <!-- OPC-UA Browser Panel -->
    <div class="opcua-browser-panel hidden" id="opcua-browser-panel">
        <div class="opcua-browser-header">
            <h3>OPC-UA Node Hierarchy</h3>
            <button class="opcua-browser-close" id="opcua-browser-close">×</button>
        </div>

        <div class="opcua-search-container">
            <input
                type="text"
                class="opcua-search-input"
                id="opcua-search-input"
                placeholder="Search nodes... (e.g., 'crusher', 'temperature')"
                autocomplete="off"
            />
        </div>

        <div class="opcua-tree-container" id="opcua-tree-container">
            <!-- Tree will be populated dynamically -->
            <div style="text-align: center; padding: 40px; color: #6B7280;">
                Loading OPC-UA hierarchy...
            </div>
        </div>
    </div>

    <!-- Sensor Selector Modal -->
    <div class="sensor-modal" id="sensor-modal">
        <div class="sensor-modal-content">
            <div class="sensor-modal-header">
                <h2 class="sensor-modal-title">Select Sensors/Tags for <span id="sensor-modal-protocol">OPC-UA</span></h2>
                <button class="sensor-modal-close" onclick="closeSensorSelector()">&times;</button>
            </div>

            <div class="sensor-modal-body">
                <!-- Filter Section -->
                <div class="sensor-filter-section">
                    <!-- Industry Filter -->
                    <div class="sensor-filter-group">
                        <label class="sensor-filter-label">Filter by Industry</label>
                        <div class="sensor-filter-options" id="industry-filter-options">
                            <!-- Will be populated dynamically -->
                        </div>
                    </div>

                    <!-- Sensor Type Filter -->
                    <div class="sensor-filter-group">
                        <label class="sensor-filter-label">Filter by Sensor Type</label>
                        <div class="sensor-filter-options" id="sensor-type-filter-options">
                            <!-- Will be populated dynamically -->
                        </div>
                    </div>

                    <!-- PLC/System Filter -->
                    <div class="sensor-filter-group">
                        <label class="sensor-filter-label">Filter by PLC/System</label>
                        <div class="sensor-filter-options" id="plc-filter-options">
                            <!-- Will be populated dynamically -->
                        </div>
                    </div>
                </div>

                <!-- Sensor List Section -->
                <div class="sensor-list-section">
                    <div class="sensor-list-header">
                        <div class="sensor-list-title">Available Sensors (<span id="filtered-sensor-count">379</span>)</div>
                        <div class="sensor-list-actions">
                            <button class="sensor-list-btn select-all" onclick="selectAllFilteredSensors()">Select All Filtered</button>
                            <button class="sensor-list-btn clear-all" onclick="clearAllSensors()">Clear All</button>
                        </div>
                    </div>
                    <div class="sensor-items-grid" id="sensor-items-grid">
                        <!-- Will be populated dynamically -->
                    </div>
                </div>
            </div>

            <div class="sensor-modal-footer">
                <div class="sensor-selection-count">
                    <strong><span id="selected-sensor-count">379</span></strong> sensors selected
                </div>
                <div class="sensor-modal-actions">
                    <button class="sensor-modal-btn cancel" onclick="closeSensorSelector()">Cancel</button>
                    <button class="sensor-modal-btn apply" onclick="applySensorSelection()">Apply Selection</button>
                </div>
            </div>
        </div>
    </div>"""


def get_scripts_html() -> str:
    """Return the JavaScript code for the web UI."""
    return """    <script>
        // Register Chart.js annotation plugin
        if (typeof Chart !== 'undefined' && typeof chartAnnotation !== 'undefined') {
            Chart.register(chartAnnotation);
        }

        // WebSocket connection
        let ws = null;
        let reconnectInterval = null;
        const charts = {};
        let conversationHistory = [];

        // Multi-sensor overlay support
        let selectedSensors = new Set();
        let overlayCharts = new Map();
        const CHART_COLORS = ['#00a8e1', '#ff3621', '#10b981', '#fbbf24', '#f97316', '#8b5cf6', '#ec4899', '#06b6d4'];

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('WebSocket connected');
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                // Attempt to reconnect
                if (!reconnectInterval) {
                    reconnectInterval = setInterval(() => {
                        console.log('Attempting to reconnect...');
                        connectWebSocket();
                    }, 5000);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }

        function handleWebSocketMessage(data) {
            if (data.type === 'sensor_data') {
                // Update charts with new data
                Object.entries(data.sensors).forEach(([sensor, value]) => {
                    updateChart(sensor, value, data.timestamp);
                });
            } else if (data.type === 'status_update') {
                // Update protocol status indicators and button states
                Object.entries(data.simulators).forEach(([protocol, status]) => {
                    const badge = document.getElementById(`status-${protocol}`);
                    const startBtn = document.getElementById(`start-${protocol}`);
                    const stopBtn = document.getElementById(`stop-${protocol}`);

                    if (badge) {
                        if (status.running) {
                            badge.classList.add('running');
                        } else {
                            badge.classList.remove('running');
                        }
                    }

                    // Update button states: if running, disable start and enable stop
                    if (startBtn && stopBtn) {
                        if (status.running) {
                            startBtn.disabled = true;
                            startBtn.style.opacity = '0.5';
                            startBtn.style.cursor = 'not-allowed';
                            stopBtn.disabled = false;
                            stopBtn.style.opacity = '1';
                            stopBtn.style.cursor = 'pointer';
                        } else {
                            startBtn.disabled = false;
                            startBtn.style.opacity = '1';
                            startBtn.style.cursor = 'pointer';
                            stopBtn.disabled = true;
                            stopBtn.style.opacity = '0.5';
                            stopBtn.style.cursor = 'not-allowed';
                        }
                    }
                });
            } else if (data.type === 'nlp_response') {
                // Handle natural language response
                console.log('NLP Response received:', data);
                removeTypingIndicator();

                let response = '';
                if (data.action === 'start') {
                    // Use backend message first, fall back to constructed message
                    response = data.message || `✓ ${data.target ? data.target.toUpperCase() : 'Protocol'} started successfully!`;
                } else if (data.action === 'stop') {
                    // Use backend message first, fall back to constructed message
                    response = data.message || `✓ ${data.target ? data.target.toUpperCase() : 'Protocol'} stopped successfully!`;
                } else if (data.action === 'inject_fault') {
                    // Use backend message first, fall back to constructed message
                    const duration = data.parameters?.duration || '?';
                    response = data.message || `✓ Fault injected into ${data.target} for ${duration}s`;
                } else if (data.action === 'status') {
                    // Show the full status message from backend
                    response = data.message || 'Status information updated';
                } else if (data.action === 'list_sensors') {
                    // Use the formatted message from backend (contains full sensor list)
                    response = data.message || `Showing ${data.target} sensors`;
                } else if (data.action === 'chat') {
                    // Use message first, reasoning second (message is usually formatted better)
                    response = data.message || data.reasoning || 'Command processed';
                } else {
                    // Default: prefer message over reasoning
                    response = data.message || data.reasoning || 'Command executed';
                }

                // Show error if command failed
                if (!data.success) {
                    response = `❌ ${data.message || 'Command failed'}`;
                }

                // For list_sensors action, don't show reasoning separately (it's redundant)
                const showReasoning = data.action !== 'list_sensors' ? data.reasoning : null;
                addMessage('agent', response, showReasoning);

                // Add to conversation history
                conversationHistory.push({
                    role: 'assistant',
                    content: response
                });
            } else if (data.type === 'error') {
                // Handle error messages
                console.error('WebSocket error:', data);
                removeTypingIndicator();
                addMessage('agent', `❌ Error: ${data.message}`);
            }
        }

        function updateChart(sensorPath, value, timestamp) {
            // Update overlay charts first
            updateOverlayChart(sensorPath, value, timestamp);

            if (!charts[sensorPath]) return;

            const chart = charts[sensorPath];
            const fftState = fftStates[sensorPath];
            const spectrogramState = spectrogramStates[sensorPath];
            const spcState = spcStates[sensorPath];

            // If in FFT mode, add to data buffer
            if (fftState && fftState.isFFT) {
                if (!fftState.dataBuffer) {
                    fftState.dataBuffer = [];
                }
                fftState.dataBuffer.push(value);

                // Keep only last 512 samples for FFT
                if (fftState.dataBuffer.length > 512) {
                    fftState.dataBuffer.shift();
                }
            }
            // If in Spectrogram mode, add to data buffer
            else if (spectrogramState && spectrogramState.isSpectrogram) {
                if (!spectrogramState.dataBuffer) {
                    spectrogramState.dataBuffer = [];
                }
                spectrogramState.dataBuffer.push(value);

                // Keep only last 512 samples for spectrogram FFT
                if (spectrogramState.dataBuffer.length > 512) {
                    spectrogramState.dataBuffer.shift();
                }
            }
            // If in SPC mode, add to data buffer
            else if (spcState && spcState.isSPC) {
                if (!spcState.dataBuffer) {
                    spcState.dataBuffer = [];
                }
                spcState.dataBuffer.push(value);

                // Keep only last 100 samples for SPC (manageable control chart)
                if (spcState.dataBuffer.length > 100) {
                    spcState.dataBuffer.shift();
                }
            }
            // Time-domain chart update (default mode)
            else {
                const date = new Date(timestamp * 1000);

                chart.data.labels.push(date);
                chart.data.datasets[0].data.push(value);

                // Keep only last 240 points (2 minutes at 500ms intervals)
                if (chart.data.labels.length > 240) {
                    chart.data.labels.shift();
                    chart.data.datasets[0].data.shift();
                }

                chart.update('none'); // Update without animation for real-time
            }

            // Update live value display (works for all modes)
            const valueDisplay = document.getElementById(`value-${sensorPath.replace(/\\//g, '-')}`);
            if (valueDisplay) {
                valueDisplay.textContent = value.toFixed(2);
            }
        }

        function createChart(sensorPath, sensorInfo) {
            const chartId = `chart-${sensorPath.replace(/\\//g, '-')}`;
            const valueId = `value-${sensorPath.replace(/\\//g, '-')}`;
            const isVibration = sensorInfo.type && (sensorInfo.type.toLowerCase().includes('vibration') || sensorInfo.type.toLowerCase().includes('vib'));

            // Protocol badges HTML
            const protocolBadgesHTML = sensorInfo.protocols && sensorInfo.protocols.length > 0
                ? sensorInfo.protocols.map(proto =>
                    `<span class="protocol-badge-mini ${proto}">${proto}</span>`
                ).join('')
                : '';

            // Add FFT button for vibration sensors
            const fftButtonHTML = isVibration
                ? `<button class="btn-fft" onclick="toggleFFT('${sensorPath}')">FFT</button>`
                : '';

            // Add Spectrogram button for vibration sensors
            const spectrogramButtonHTML = isVibration
                ? `<button class="btn-spectrogram" onclick="toggleSpectrogram('${sensorPath}')">Spectrogram</button>`
                : '';

            // Add SPC button for all sensors
            const spcButtonHTML = `<button class="btn-spc" onclick="toggleSPC('${sensorPath}')">SPC</button>`;

            const chartHtml = `
                <div class="chart-card" id="card-${sensorPath.replace(/\\//g, '-')}">
                    <div class="chart-header">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div class="chart-title">${sensorPath}</div>
                                <div class="protocol-badges">${protocolBadgesHTML}</div>
                            </div>
                            <div class="live-value" id="${valueId}">--</div>
                        </div>
                        <div class="chart-buttons">
                            ${fftButtonHTML}
                            ${spectrogramButtonHTML}
                            ${spcButtonHTML}
                            <button class="btn btn-stop" onclick="removeChart('${sensorPath}')">×</button>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="${chartId}"></canvas>
                    </div>
                </div>
            `;

            document.getElementById('chart-section').insertAdjacentHTML('beforeend', chartHtml);

            const ctx = document.getElementById(chartId);
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: `${sensorPath} (${sensorInfo.unit})`,
                        data: [],
                        borderColor: '#FF3621',
                        backgroundColor: 'rgba(255, 54, 33, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                displayFormats: {
                                    second: 'HH:mm:ss'
                                }
                            },
                            title: {
                                display: true,
                                text: 'Time',
                                color: '#A0A4A8',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            ticks: {
                                color: '#A0A4A8',
                                maxRotation: 0
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            }
                        },
                        y: {
                            beginAtZero: sensorInfo.min_value >= 0,
                            min: sensorInfo.min_value,
                            max: sensorInfo.max_value,
                            title: {
                                display: true,
                                text: `${sensorInfo.type || 'Value'} (${sensorInfo.unit})`,
                                color: '#A0A4A8',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            ticks: {
                                color: '#A0A4A8'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(26, 31, 58, 0.98)',
                            titleColor: '#E8EAED',
                            bodyColor: '#A0A4A8',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            padding: 12,
                            displayColors: false
                        }
                    },
                    // Store sensorInfo for FFT toggle
                    sensorInfo: sensorInfo
                }
            });

            charts[sensorPath] = chart;

            // Subscribe to sensor via WebSocket
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'subscribe',
                    sensors: [sensorPath]
                }));
            }
        }

        function removeChart(sensorPath) {
            // Unsubscribe from sensor
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'unsubscribe',
                    sensors: [sensorPath]
                }));
            }

            // Clear FFT update interval if exists (but keep fftStates for toggle)
            if (fftStates[sensorPath] && fftStates[sensorPath].updateInterval) {
                clearInterval(fftStates[sensorPath].updateInterval);
                fftStates[sensorPath].updateInterval = null;
                // Don't delete fftStates - keep it for toggle back to FFT mode
            }

            // Clear Spectrogram update interval if exists (but keep spectrogramStates for toggle)
            if (spectrogramStates[sensorPath] && spectrogramStates[sensorPath].updateInterval) {
                clearInterval(spectrogramStates[sensorPath].updateInterval);
                spectrogramStates[sensorPath].updateInterval = null;
                // Don't delete spectrogramStates - keep it for toggle back
            }

            // Clear SPC update interval if exists (but keep spcStates for toggle)
            if (spcStates[sensorPath] && spcStates[sensorPath].updateInterval) {
                clearInterval(spcStates[sensorPath].updateInterval);
                spcStates[sensorPath].updateInterval = null;
                // Don't delete spcStates - keep it for toggle back
            }

            // Remove chart
            if (charts[sensorPath]) {
                charts[sensorPath].destroy();
                delete charts[sensorPath];
            }

            // Remove DOM element
            const cardId = `card-${sensorPath.replace(/\\//g, '-')}`;
            document.getElementById(cardId)?.remove();
        }

        function startProtocol(protocol) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'nlp_command',
                    text: `start ${protocol}`
                }));
            }
        }

        function stopProtocol(protocol) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'nlp_command',
                    text: `stop ${protocol}`
                }));
            }
        }

        // Multi-Sensor Overlay Functions
        function toggleSensorSelection(sensorPath, sensorInfo, sensorItem) {
            if (selectedSensors.has(sensorPath)) {
                selectedSensors.delete(sensorPath);
                sensorItem.classList.remove('selected');
            } else {
                selectedSensors.add(sensorPath);
                sensorItem.classList.add('selected');
                // Store sensor info for later use
                if (!sensorItem.dataset.sensorInfo) {
                    sensorItem.dataset.sensorInfo = JSON.stringify(sensorInfo);
                }
            }

            // Show/update overlay button
            updateOverlayButton();
        }

        function updateOverlayButton() {
            let overlayBtn = document.getElementById('create-overlay-btn');

            if (selectedSensors.size === 0) {
                // Remove button if no sensors selected
                if (overlayBtn) overlayBtn.remove();
                return;
            }

            if (!overlayBtn) {
                // Create button
                overlayBtn = document.createElement('button');
                overlayBtn.id = 'create-overlay-btn';
                overlayBtn.style.cssText = `
                    position: fixed;
                    bottom: 24px;
                    right: 24px;
                    padding: 16px 24px;
                    background: linear-gradient(135deg, #00A9E0 0%, #0080B3 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 14px;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0, 169, 224, 0.3);
                    z-index: 1000;
                    transition: all 0.3s;
                `;
                overlayBtn.onmouseover = function() {
                    this.style.transform = 'translateY(-2px)';
                    this.style.boxShadow = '0 6px 16px rgba(0, 169, 224, 0.4)';
                };
                overlayBtn.onmouseout = function() {
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = '0 4px 12px rgba(0, 169, 224, 0.3)';
                };
                overlayBtn.onclick = createOverlayChart;
                document.body.appendChild(overlayBtn);
            }

            overlayBtn.textContent = `Create Overlay Chart (${selectedSensors.size} sensor${selectedSensors.size !== 1 ? 's' : ''})`;
        }

        function createOverlayChart() {
            if (selectedSensors.size === 0) return;

            const chartId = 'overlay-' + Date.now();
            const sensorsArray = Array.from(selectedSensors);

            // Get sensor metadata from DOM
            const sensorMetadata = sensorsArray.map(path => {
                const sensorItem = document.querySelector(`[onclick*="${path}"]`);
                if (sensorItem && sensorItem.dataset.sensorInfo) {
                    return { path, ...JSON.parse(sensorItem.dataset.sensorInfo) };
                }
                // Fallback - extract from path
                const parts = path.split('/');
                return {
                    path,
                    name: parts[parts.length - 1],
                    unit: 'unit',
                    type: 'sensor'
                };
            });

            // Group by unit for Y-axis assignment
            const unitGroups = {};
            sensorMetadata.forEach(s => {
                const unit = s.unit || 'unknown';
                if (!unitGroups[unit]) unitGroups[unit] = [];
                unitGroups[unit].push(s);
            });

            // Create chart container
            const chartSection = document.getElementById('chart-section');
            const cardDiv = document.createElement('div');
            cardDiv.className = 'card';
            cardDiv.id = `card-${chartId}`;
            cardDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="color: #00A9E0; font-size: 18px; font-weight: 600;">Multi-Sensor Overlay (${sensorsArray.length} sensors)</h3>
                    <div>
                        <button class="btn btn-stop" onclick="removeOverlayChart('${chartId}')" style="background: #EF4444; color: white; padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer;">Remove</button>
                    </div>
                </div>
                <div style="position: relative; height: 400px;">
                    <canvas id="${chartId}"></canvas>
                </div>
                <div id="${chartId}-correlation" style="margin-top: 12px; padding: 12px; background: #F3F4F6; border-radius: 6px; font-size: 14px; color: #4B5563;"></div>
            `;
            chartSection.insertBefore(cardDiv, chartSection.firstChild);

            // Create datasets
            const datasets = sensorMetadata.map((sensor, i) => ({
                label: sensor.name + ' (' + sensor.unit + ')',
                data: [],
                borderColor: CHART_COLORS[i % CHART_COLORS.length],
                backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + '33',
                yAxisID: 'y' + Object.keys(unitGroups).indexOf(sensor.unit || 'unknown'),
                tension: 0.3,
                pointRadius: 0,
                borderWidth: 2
            }));

            // Create Y-axes
            const scales = {
                x: {
                    type: 'time',
                    time: { unit: 'second' },
                    title: { display: true, text: 'Time', color: '#6B7280' },
                    ticks: { color: '#6B7280' },
                    grid: { color: '#E5E7EB' }
                }
            };

            Object.keys(unitGroups).forEach((unit, i) => {
                scales['y' + i] = {
                    type: 'linear',
                    position: i % 2 === 0 ? 'left' : 'right',
                    title: { display: true, text: unit, color: '#6B7280' },
                    ticks: { color: '#6B7280' },
                    grid: { drawOnChartArea: i === 0, color: '#E5E7EB' }
                };
            });

            // Create chart
            const ctx = document.getElementById(chartId).getContext('2d');
            const chart = new Chart(ctx, {
                type: 'line',
                data: { datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales,
                    plugins: {
                        legend: {
                            display: true,
                            labels: { color: '#2E3036' }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                }
            });

            overlayCharts.set(chartId, { chart, sensors: sensorsArray, metadata: sensorMetadata });

            // Subscribe to all sensors
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'subscribe',
                    sensors: sensorsArray
                }));
            }

            // Clear selection
            selectedSensors.clear();
            document.querySelectorAll('.sensor-item.selected').forEach(item => {
                item.classList.remove('selected');
            });
            updateOverlayButton();
        }

        function removeOverlayChart(chartId) {
            const chartData = overlayCharts.get(chartId);
            if (chartData) {
                // Unsubscribe from sensors
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'unsubscribe',
                        sensors: chartData.sensors
                    }));
                }

                // Destroy chart
                chartData.chart.destroy();
                overlayCharts.delete(chartId);
            }

            // Remove DOM element
            document.getElementById(`card-${chartId}`)?.remove();
        }

        function updateOverlayChart(sensorPath, value, timestamp) {
            // Update all overlay charts that contain this sensor
            overlayCharts.forEach((chartData, chartId) => {
                const sensorIndex = chartData.sensors.indexOf(sensorPath);
                if (sensorIndex !== -1) {
                    const chart = chartData.chart;
                    const dataset = chart.data.datasets[sensorIndex];

                    // Add new data point
                    dataset.data.push({ x: timestamp, y: value });

                    // Keep last 100 points
                    if (dataset.data.length > 100) {
                        dataset.data.shift();
                    }

                    chart.update('none');

                    // Update correlation display
                    updateCorrelationDisplay(chartId);
                }
            });
        }

        function updateCorrelationDisplay(chartId) {
            const chartData = overlayCharts.get(chartId);
            if (!chartData || chartData.sensors.length < 2) return;

            const correlations = [];
            const datasets = chartData.chart.data.datasets;

            for (let i = 0; i < datasets.length - 1; i++) {
                for (let j = i + 1; j < datasets.length; j++) {
                    const data1 = datasets[i].data.map(d => d.y);
                    const data2 = datasets[j].data.map(d => d.y);

                    if (data1.length >= 10 && data2.length >= 10) {
                        const r = pearsonCorrelation(data1, data2);
                        if (!isNaN(r)) {
                            correlations.push({
                                pair: `${chartData.metadata[i].name} ↔ ${chartData.metadata[j].name}`,
                                correlation: r.toFixed(3)
                            });
                        }
                    }
                }
            }

            const corrDiv = document.getElementById(chartId + '-correlation');
            if (corrDiv && correlations.length > 0) {
                corrDiv.innerHTML = '<strong>Pearson Correlations:</strong> ' +
                    correlations.map(c => `${c.pair}: r=${c.correlation}`).join(' | ');
            }
        }

        function pearsonCorrelation(x, y) {
            const n = Math.min(x.length, y.length);
            if (n < 2) return 0;

            const xMean = x.slice(0, n).reduce((a, b) => a + b, 0) / n;
            const yMean = y.slice(0, n).reduce((a, b) => a + b, 0) / n;

            let num = 0, denX = 0, denY = 0;
            for (let i = 0; i < n; i++) {
                const dx = x[i] - xMean;
                const dy = y[i] - yMean;
                num += dx * dy;
                denX += dx * dx;
                denY += dy * dy;
            }

            return num / Math.sqrt(denX * denY);
        }

        // FFT Analysis Functions
        const fftStates = {}; // Track FFT state per sensor

        function toggleFFT(sensorPath) {
            const chart = charts[sensorPath];
            if (!chart) return;

            const button = document.querySelector(`[onclick="toggleFFT('${sensorPath}')"]`);
            const isFFTMode = fftStates[sensorPath]?.isFFT || false;

            if (isFFTMode) {
                // Switch back to time domain
                fftStates[sensorPath].isFFT = false;
                button.classList.remove('active');
                button.textContent = 'FFT';

                // Recreate as time-domain chart
                const cardId = `card-${sensorPath.replace(/\\//g, '-')}`;
                const card = document.getElementById(cardId);
                const sensorInfo = fftStates[sensorPath].sensorInfo;

                // Store the button HTML before removing
                const buttonsHTML = card.querySelector('.chart-buttons').innerHTML;

                // Remove and recreate
                removeChart(sensorPath);
                createChart(sensorPath, sensorInfo);
            } else {
                // Switch to FFT mode
                fftStates[sensorPath] = fftStates[sensorPath] || {};
                fftStates[sensorPath].isFFT = true;
                fftStates[sensorPath].sensorInfo = chart.options.sensorInfo || {};
                button.classList.add('active');
                button.textContent = 'Time';

                // Convert to FFT chart
                createFFTChart(sensorPath, chart);
            }
        }

        function createFFTChart(sensorPath, timeChart) {
            const chartId = `chart-${sensorPath.replace(/\\//g, '-')}`;

            // Destroy existing time-domain chart
            timeChart.destroy();

            // Create FFT chart (bar chart for frequency domain)
            const ctx = document.getElementById(chartId);
            const fftChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: [], // Frequency bins (Hz)
                    datasets: [{
                        label: 'Amplitude (g RMS)',
                        data: [],
                        backgroundColor: 'rgba(255, 54, 33, 0.8)',
                        borderColor: '#FF3621',
                        borderWidth: 1,
                        barPercentage: 0.95,
                        categoryPercentage: 1.0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales: {
                        x: {
                            type: 'category',
                            title: {
                                display: true,
                                text: 'Frequency (Hz)',
                                color: '#A0A4A8',
                                font: { size: 12, weight: 'bold' }
                            },
                            ticks: {
                                color: '#A0A4A8',
                                maxRotation: 45,
                                minRotation: 45,
                                autoSkip: true,
                                maxTicksLimit: 20
                            },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' }
                        },
                        y: {
                            type: 'logarithmic',
                            title: {
                                display: true,
                                text: 'Amplitude (g RMS)',
                                color: '#A0A4A8',
                                font: { size: 12, weight: 'bold' }
                            },
                            ticks: {
                                color: '#A0A4A8',
                                callback: function(value) {
                                    return value.toExponential(2);
                                }
                            },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            min: 0.0001
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(26, 31, 58, 0.98)',
                            titleColor: '#E8EAED',
                            bodyColor: '#A0A4A8',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            padding: 12,
                            callbacks: {
                                title: (items) => `${items[0].label} Hz`,
                                label: (item) => `Amplitude: ${item.parsed.y.toFixed(4)} g`
                            }
                        },
                        annotation: {
                            annotations: getBearingFrequencyAnnotations()
                        }
                    }
                }
            });

            // Store FFT chart
            charts[sensorPath] = fftChart;

            // Start FFT computation interval
            startFFTUpdates(sensorPath);
        }

        function getBearingFrequencyAnnotations() {
            // Bearing defect frequencies for typical motor bearing
            // BPFO (Ball Pass Frequency Outer): 107.5 Hz
            // BPFI (Ball Pass Frequency Inner): 162.5 Hz
            // BSF (Ball Spin Frequency): 42.8 Hz
            // FTF (Fundamental Train Frequency): 16.2 Hz

            return {
                bpfo: {
                    type: 'line',
                    xMin: 107.5,
                    xMax: 107.5,
                    borderColor: '#FF3621',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    label: {
                        display: true,
                        content: 'BPFO',
                        position: 'start',
                        backgroundColor: '#FF3621',
                        color: 'white',
                        font: { size: 10, weight: 'bold' }
                    }
                },
                bpfi: {
                    type: 'line',
                    xMin: 162.5,
                    xMax: 162.5,
                    borderColor: '#00A9E0',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    label: {
                        display: true,
                        content: 'BPFI',
                        position: 'start',
                        backgroundColor: '#00A9E0',
                        color: 'white',
                        font: { size: 10, weight: 'bold' }
                    }
                },
                bsf: {
                    type: 'line',
                    xMin: 42.8,
                    xMax: 42.8,
                    borderColor: '#10B981',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    label: {
                        display: true,
                        content: 'BSF',
                        position: 'start',
                        backgroundColor: '#10B981',
                        color: 'white',
                        font: { size: 10, weight: 'bold' }
                    }
                },
                ftf: {
                    type: 'line',
                    xMin: 16.2,
                    xMax: 16.2,
                    borderColor: '#FBBF24',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    label: {
                        display: true,
                        content: 'FTF',
                        position: 'start',
                        backgroundColor: '#FBBF24',
                        color: 'white',
                        font: { size: 10, weight: 'bold' }
                    }
                }
            };
        }

        function startFFTUpdates(sensorPath) {
            // Store time-domain data buffer for FFT computation
            if (!fftStates[sensorPath]) {
                fftStates[sensorPath] = {};
            }

            // Initialize data buffer if not already exists
            if (!fftStates[sensorPath].dataBuffer) {
                fftStates[sensorPath].dataBuffer = [];
            }

            // Update FFT every 500ms
            fftStates[sensorPath].updateInterval = setInterval(() => {
                computeAndUpdateFFT(sensorPath);
            }, 500);
        }

        function computeAndUpdateFFT(sensorPath) {
            const chart = charts[sensorPath];
            const state = fftStates[sensorPath];

            if (!chart || !state || !state.dataBuffer || state.dataBuffer.length < 8) {
                console.log(`FFT: Waiting for data... Buffer size: ${state?.dataBuffer?.length || 0}`);
                return; // Need at least 8 samples for FFT (will round to power of 2)
            }

            // Get last 256 samples from buffer (power of 2 for FFT)
            const bufferSize = Math.min(256, Math.pow(2, Math.floor(Math.log2(state.dataBuffer.length))));
            const samples = state.dataBuffer.slice(-bufferSize);
            console.log(`FFT: Computing with ${bufferSize} samples from buffer of ${state.dataBuffer.length}`);

            // Compute FFT using fft.js library
            const fft = new FFTNayuki(bufferSize);
            const real = new Array(bufferSize);
            const imag = new Array(bufferSize);

            // Copy samples and apply Hanning window
            for (let i = 0; i < bufferSize; i++) {
                const window = 0.5 * (1 - Math.cos(2 * Math.PI * i / (bufferSize - 1)));
                real[i] = samples[i] * window;
                imag[i] = 0;
            }

            // Perform FFT
            fft.transform(real, imag);

            // Compute magnitudes and frequency bins
            const sampleRate = 2; // 2 Hz (500ms updates)
            const freqResolution = sampleRate / bufferSize;
            const numBins = Math.floor(bufferSize / 2); // Only positive frequencies

            const frequencies = [];
            const magnitudes = [];

            for (let i = 0; i < numBins; i++) {
                const freq = i * freqResolution;
                if (freq <= 500) { // Only show up to 500 Hz
                    frequencies.push(freq.toFixed(1));
                    const magnitude = Math.sqrt(real[i] * real[i] + imag[i] * imag[i]) / bufferSize;
                    magnitudes.push(magnitude);
                }
            }

            // Update chart
            chart.data.labels = frequencies;
            chart.data.datasets[0].data = magnitudes;
            chart.update('none');

            console.log(`FFT: Updated chart with ${frequencies.length} frequency bins (0 to ${frequencies[frequencies.length-1]} Hz)`);
            console.log(`FFT: Magnitude range: ${Math.min(...magnitudes).toExponential(2)} to ${Math.max(...magnitudes).toExponential(2)}`);
        }

        // Simple FFT implementation (Cooley-Tukey algorithm)
        class FFTNayuki {
            constructor(n) {
                this.n = n;
                this.levels = Math.log2(n);
                if (Math.pow(2, this.levels) !== n) {
                    throw new Error('FFT size must be power of 2');
                }
            }

            transform(real, imag) {
                const n = this.n;

                // Bit-reversal permutation
                for (let i = 0; i < n; i++) {
                    const j = this.reverseBits(i, this.levels);
                    if (j > i) {
                        [real[i], real[j]] = [real[j], real[i]];
                        [imag[i], imag[j]] = [imag[j], imag[i]];
                    }
                }

                // Cooley-Tukey decimation-in-time FFT
                for (let size = 2; size <= n; size *= 2) {
                    const halfsize = size / 2;
                    const tablestep = n / size;
                    for (let i = 0; i < n; i += size) {
                        for (let j = i, k = 0; j < i + halfsize; j++, k += tablestep) {
                            const tpre = real[j + halfsize] * Math.cos(2 * Math.PI * k / n) +
                                        imag[j + halfsize] * Math.sin(2 * Math.PI * k / n);
                            const tpim = -real[j + halfsize] * Math.sin(2 * Math.PI * k / n) +
                                         imag[j + halfsize] * Math.cos(2 * Math.PI * k / n);
                            real[j + halfsize] = real[j] - tpre;
                            imag[j + halfsize] = imag[j] - tpim;
                            real[j] += tpre;
                            imag[j] += tpim;
                        }
                    }
                }
            }

            reverseBits(x, bits) {
                let y = 0;
                for (let i = 0; i < bits; i++) {
                    y = (y << 1) | (x & 1);
                    x >>>= 1;
                }
                return y;
            }
        }

        // ========================================
        // SPECTROGRAM (Time-Frequency Heatmap)
        // ========================================
        const spectrogramStates = {}; // Track spectrogram state per sensor

        function toggleSpectrogram(sensorPath) {
            const chart = charts[sensorPath];
            if (!chart) return;

            const button = document.querySelector(`[onclick="toggleSpectrogram('${sensorPath}')"]`);
            const isSpectrogramMode = spectrogramStates[sensorPath]?.isSpectrogram || false;

            if (isSpectrogramMode) {
                // Switch back to time domain
                spectrogramStates[sensorPath].isSpectrogram = false;
                button.classList.remove('active');
                button.textContent = 'Spectrogram';

                // Recreate as time-domain chart
                const cardId = `card-${sensorPath.replace(/\//g, '-')}`;
                const card = document.getElementById(cardId);
                if (card && spectrogramStates[sensorPath].sensorInfo) {
                    removeChart(sensorPath);
                    createChart(sensorPath, spectrogramStates[sensorPath].sensorInfo);
                }
            } else {
                // Switch to spectrogram mode
                spectrogramStates[sensorPath] = {
                    isSpectrogram: true,
                    sensorInfo: chart.options.sensorInfo,
                    dataBuffer: [],
                    spectrogramData: [], // Array of FFT results over time
                    maxSpectrogramRows: 60 // Keep last 60 FFT computations (30 seconds @ 500ms)
                };
                button.classList.add('active');
                button.textContent = 'Time';

                createSpectrogramChart(sensorPath, chart);
            }
        }

        function createSpectrogramChart(sensorPath, timeChart) {
            const chartId = `chart-${sensorPath.replace(/\//g, '-')}`;

            // Destroy existing time-domain chart
            timeChart.destroy();

            // Create spectrogram heatmap using Chart.js matrix plugin (if available)
            // For now, we'll use a simplified approach with horizontal bars representing time slices
            const ctx = document.getElementById(chartId);
            const spectrogramChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: [], // Time labels
                    datasets: [] // Will be dynamically created for each frequency bin
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales: {
                        x: {
                            type: 'category',
                            title: {
                                display: true,
                                text: 'Time (seconds ago)',
                                color: '#fff'
                            },
                            ticks: {
                                color: '#9CA3AF',
                                maxRotation: 0,
                                autoSkip: true,
                                maxTicksLimit: 10
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y: {
                            type: 'linear',
                            title: {
                                display: true,
                                text: 'Frequency (Hz)',
                                color: '#fff'
                            },
                            ticks: {
                                color: '#9CA3AF'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            enabled: true,
                            callbacks: {
                                label: function(context) {
                                    return `Frequency: ${context.label} Hz, Magnitude: ${context.parsed.y.toFixed(4)} g`;
                                }
                            }
                        },
                        annotation: {
                            annotations: {
                                info: {
                                    type: 'label',
                                    xValue: 0,
                                    yValue: 0.8,
                                    content: ['Spectrogram: Time-Frequency Evolution', 'Darker = Higher Amplitude'],
                                    color: '#9CA3AF',
                                    font: {
                                        size: 10
                                    }
                                }
                            }
                        }
                    },
                    sensorInfo: timeChart.options.sensorInfo // Preserve for toggle
                }
            });

            charts[sensorPath] = spectrogramChart;
            startSpectrogramUpdates(sensorPath);
        }

        function startSpectrogramUpdates(sensorPath) {
            const state = spectrogramStates[sensorPath];
            if (!state) return;

            // Initialize data buffer
            if (!state.dataBuffer) {
                state.dataBuffer = [];
            }

            // Update every 500ms
            state.updateInterval = setInterval(() => {
                computeAndUpdateSpectrogram(sensorPath);
            }, 500);
        }

        function computeAndUpdateSpectrogram(sensorPath) {
            const chart = charts[sensorPath];
            const state = spectrogramStates[sensorPath];

            if (!chart || !state || !state.dataBuffer || state.dataBuffer.length < 8) {
                return;
            }

            const bufferSize = Math.min(64, Math.pow(2, Math.floor(Math.log2(state.dataBuffer.length))));
            const samples = state.dataBuffer.slice(-bufferSize);

            // Compute FFT
            const real = new Array(bufferSize);
            const imag = new Array(bufferSize);

            // Apply Hanning window
            for (let i = 0; i < bufferSize; i++) {
                const window = 0.5 * (1 - Math.cos(2 * Math.PI * i / (bufferSize - 1)));
                real[i] = samples[i] * window;
                imag[i] = 0;
            }

            const fft = new FFTNayuki(bufferSize);
            fft.transform(real, imag);

            // Compute magnitudes for first half (positive frequencies)
            const freqBins = [];
            const magnitudes = [];
            const sampleRate = 2; // 2 Hz (500ms updates)
            const numBins = bufferSize / 2;

            for (let i = 0; i < numBins; i++) {
                const freq = (i * sampleRate) / bufferSize;
                const magnitude = Math.sqrt(real[i] * real[i] + imag[i] * imag[i]) / bufferSize;
                freqBins.push(freq.toFixed(3));
                magnitudes.push(magnitude);
            }

            // Add this FFT result to spectrogram history
            state.spectrogramData.push({
                timestamp: Date.now(),
                freqBins: freqBins,
                magnitudes: magnitudes
            });

            // Keep only last maxSpectrogramRows
            if (state.spectrogramData.length > state.maxSpectrogramRows) {
                state.spectrogramData.shift();
            }

            // Update chart: Create a heatmap-style visualization
            // We'll use stacked horizontal bars with color intensity based on magnitude
            updateSpectrogramChart(chart, state);
        }

        function updateSpectrogramChart(chart, state) {
            if (state.spectrogramData.length === 0) return;

            // Get the most recent FFT result
            const latestFFT = state.spectrogramData[state.spectrogramData.length - 1];

            // Create scatter plot with bubbles sized by magnitude
            const scatterData = [];
            const now = Date.now();

            state.spectrogramData.forEach((fftResult, timeIndex) => {
                const secondsAgo = ((now - fftResult.timestamp) / 1000).toFixed(1);

                fftResult.magnitudes.forEach((magnitude, freqIndex) => {
                    if (magnitude > 0.0001) { // Filter out noise
                        scatterData.push({
                            x: secondsAgo,
                            y: parseFloat(fftResult.freqBins[freqIndex]),
                            r: Math.min(10, Math.max(2, magnitude * 1000)) // Bubble size
                        });
                    }
                });
            });

            // Update chart with bubble data
            chart.data.datasets = [{
                type: 'bubble',
                label: 'Magnitude',
                data: scatterData,
                backgroundColor: 'rgba(139, 92, 246, 0.6)',
                borderColor: 'rgba(139, 92, 246, 0.9)'
            }];

            // Update time labels
            const timeLabels = state.spectrogramData.map((fft, i) => {
                const secondsAgo = ((now - fft.timestamp) / 1000).toFixed(1);
                return secondsAgo;
            });

            chart.data.labels = latestFFT.freqBins; // Use frequency bins as labels
            chart.update('none');
        }

        // ========================================
        // SPC CHARTS (Statistical Process Control)
        // ========================================
        const spcStates = {}; // Track SPC state per sensor

        function toggleSPC(sensorPath) {
            const chart = charts[sensorPath];
            if (!chart) return;

            const button = document.querySelector(`[onclick="toggleSPC('${sensorPath}')"]`);
            const isSPCMode = spcStates[sensorPath]?.isSPC || false;

            if (isSPCMode) {
                // Switch back to time domain
                spcStates[sensorPath].isSPC = false;
                button.classList.remove('active');
                button.textContent = 'SPC';

                // Recreate as time-domain chart
                const cardId = `card-${sensorPath.replace(/\//g, '-')}`;
                const card = document.getElementById(cardId);
                if (card && spcStates[sensorPath].sensorInfo) {
                    removeChart(sensorPath);
                    createChart(sensorPath, spcStates[sensorPath].sensorInfo);
                }
            } else {
                // Switch to SPC mode
                spcStates[sensorPath] = {
                    isSPC: true,
                    sensorInfo: chart.options.sensorInfo,
                    dataBuffer: [],
                    mean: null,
                    stdDev: null,
                    ucl: null, // Upper Control Limit (+3σ)
                    lcl: null, // Lower Control Limit (-3σ)
                    uwl: null, // Upper Warning Limit (+2σ)
                    lwl: null  // Lower Warning Limit (-2σ)
                };
                button.classList.add('active');
                button.textContent = 'Time';

                createSPCChart(sensorPath, chart);
            }
        }

        function createSPCChart(sensorPath, timeChart) {
            const chartId = `chart-${sensorPath.replace(/\//g, '-')}`;

            // Destroy existing time-domain chart
            timeChart.destroy();

            // Create SPC chart with control limits
            const ctx = document.getElementById(chartId);
            const spcChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Value',
                            data: [],
                            borderColor: '#00A9E0',
                            backgroundColor: 'rgba(0, 169, 224, 0.1)',
                            pointBackgroundColor: '#00A9E0',
                            pointRadius: 4,
                            tension: 0.1,
                            order: 1
                        },
                        {
                            label: 'Mean',
                            data: [],
                            borderColor: '#059669',
                            borderDash: [5, 5],
                            pointRadius: 0,
                            borderWidth: 2,
                            order: 2
                        },
                        {
                            label: 'UCL (+3σ)',
                            data: [],
                            borderColor: '#EF4444',
                            borderDash: [10, 5],
                            pointRadius: 0,
                            borderWidth: 2,
                            order: 3
                        },
                        {
                            label: 'LCL (-3σ)',
                            data: [],
                            borderColor: '#EF4444',
                            borderDash: [10, 5],
                            pointRadius: 0,
                            borderWidth: 2,
                            order: 4
                        },
                        {
                            label: 'UWL (+2σ)',
                            data: [],
                            borderColor: '#F59E0B',
                            borderDash: [5, 3],
                            pointRadius: 0,
                            borderWidth: 1,
                            order: 5
                        },
                        {
                            label: 'LWL (-2σ)',
                            data: [],
                            borderColor: '#F59E0B',
                            borderDash: [5, 3],
                            pointRadius: 0,
                            borderWidth: 1,
                            order: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales: {
                        x: {
                            type: 'category',
                            title: {
                                display: true,
                                text: 'Sample Number',
                                color: '#fff'
                            },
                            ticks: {
                                color: '#9CA3AF',
                                maxRotation: 0,
                                autoSkip: true,
                                maxTicksLimit: 15
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y: {
                            type: 'linear',
                            title: {
                                display: true,
                                text: `Value (${timeChart.data.datasets[0].label})`,
                                color: '#fff'
                            },
                            ticks: {
                                color: '#9CA3AF'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            labels: {
                                color: '#9CA3AF',
                                font: {
                                    size: 10
                                },
                                filter: function(item) {
                                    return !item.text.includes('Warning'); // Hide warning limits from legend
                                }
                            }
                        },
                        tooltip: {
                            enabled: true,
                            callbacks: {
                                label: function(context) {
                                    if (context.dataset.label === 'Value') {
                                        return `Value: ${context.parsed.y.toFixed(2)}`;
                                    }
                                    return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    sensorInfo: timeChart.options.sensorInfo // Preserve for toggle
                }
            });

            charts[sensorPath] = spcChart;
            startSPCUpdates(sensorPath);
        }

        function startSPCUpdates(sensorPath) {
            const state = spcStates[sensorPath];
            if (!state) return;

            // Initialize data buffer
            if (!state.dataBuffer) {
                state.dataBuffer = [];
            }

            // Update every 500ms
            state.updateInterval = setInterval(() => {
                updateSPCChart(sensorPath);
            }, 500);
        }

        function updateSPCChart(sensorPath) {
            const chart = charts[sensorPath];
            const state = spcStates[sensorPath];

            if (!chart || !state) return;

            // Get latest data from buffer
            if (!state.dataBuffer || state.dataBuffer.length < 20) {
                // Need at least 20 samples to compute meaningful statistics
                return;
            }

            // Compute statistics (mean and standard deviation)
            const n = state.dataBuffer.length;
            state.mean = state.dataBuffer.reduce((sum, val) => sum + val, 0) / n;

            const squaredDiffs = state.dataBuffer.map(val => Math.pow(val - state.mean, 2));
            state.stdDev = Math.sqrt(squaredDiffs.reduce((sum, val) => sum + val, 0) / n);

            // Compute control limits
            state.ucl = state.mean + (3 * state.stdDev); // Upper Control Limit
            state.lcl = state.mean - (3 * state.stdDev); // Lower Control Limit
            state.uwl = state.mean + (2 * state.stdDev); // Upper Warning Limit
            state.lwl = state.mean - (2 * state.stdDev); // Lower Warning Limit

            // Update chart datasets
            const labels = state.dataBuffer.map((_, i) => i + 1);
            const meanLine = state.dataBuffer.map(_ => state.mean);
            const uclLine = state.dataBuffer.map(_ => state.ucl);
            const lclLine = state.dataBuffer.map(_ => state.lcl);
            const uwlLine = state.dataBuffer.map(_ => state.uwl);
            const lwlLine = state.dataBuffer.map(_ => state.lwl);

            // Color points based on control limits
            const pointColors = state.dataBuffer.map(val => {
                if (val > state.ucl || val < state.lcl) {
                    return '#EF4444'; // Red: Out of control
                } else if (val > state.uwl || val < state.lwl) {
                    return '#F59E0B'; // Yellow: Warning
                } else {
                    return '#00A9E0'; // Blue: In control
                }
            });

            chart.data.labels = labels;
            chart.data.datasets[0].data = state.dataBuffer;
            chart.data.datasets[0].pointBackgroundColor = pointColors;
            chart.data.datasets[1].data = meanLine;
            chart.data.datasets[2].data = uclLine;
            chart.data.datasets[3].data = lclLine;
            chart.data.datasets[4].data = uwlLine;
            chart.data.datasets[5].data = lwlLine;

            chart.update('none');
        }

        // ========================================
        // CORRELATION HEATMAP MATRIX
        // ========================================
        let correlationHeatmapVisible = false;

        function createCorrelationHeatmap() {
            if (correlationHeatmapVisible) {
                // Hide existing heatmap
                const existingCard = document.getElementById('correlation-heatmap-card');
                if (existingCard) {
                    existingCard.remove();
                    correlationHeatmapVisible = false;
                }
                return;
            }

            // Get all active sensors
            const activeSensors = Object.keys(charts);
            if (activeSensors.length < 2) {
                alert('Please create at least 2 charts to see correlation heatmap');
                return;
            }

            // Create correlation matrix
            const correlationMatrix = {};
            activeSensors.forEach(sensor1 => {
                correlationMatrix[sensor1] = {};
                activeSensors.forEach(sensor2 => {
                    if (sensor1 === sensor2) {
                        correlationMatrix[sensor1][sensor2] = 1.0;
                    } else {
                        // Compute Pearson correlation
                        const chart1 = charts[sensor1];
                        const chart2 = charts[sensor2];
                        if (chart1.data.datasets[0].data.length > 1 && chart2.data.datasets[0].data.length > 1) {
                            const r = pearsonCorrelation(
                                chart1.data.datasets[0].data,
                                chart2.data.datasets[0].data
                            );
                            correlationMatrix[sensor1][sensor2] = r;
                        } else {
                            correlationMatrix[sensor1][sensor2] = 0;
                        }
                    }
                });
            });

            // Create heatmap visualization
            const chartHtml = `
                <div class="chart-card" id="correlation-heatmap-card" style="grid-column: 1 / -1; min-height: ${activeSensors.length * 40 + 200}px;">
                    <div class="chart-header">
                        <div class="chart-title">Correlation Heatmap Matrix</div>
                        <button class="btn btn-stop" onclick="createCorrelationHeatmap()">×</button>
                    </div>
                    <div class="chart-container">
                        <canvas id="correlation-heatmap-chart"></canvas>
                    </div>
                    <div style="padding: 12px; font-size: 11px; color: #9CA3AF; border-top: 1px solid rgba(255,255,255,0.1);">
                        <strong>Interpretation:</strong>
                        <span style="color: #EF4444;">Red (1.0)</span> = Perfect positive correlation,
                        <span style="color: #F59E0B;">Yellow (0.5)</span> = Moderate correlation,
                        <span style="color: #6B7280;">Gray (0.0)</span> = No correlation,
                        <span style="color: #3B82F6;">Blue (-1.0)</span> = Perfect negative correlation
                    </div>
                </div>
            `;

            document.getElementById('chart-section').insertAdjacentHTML('beforeend', chartHtml);

            // Create matrix visualization using Chart.js
            const ctx = document.getElementById('correlation-heatmap-chart');

            // Prepare matrix data for visualization
            const matrixData = [];
            activeSensors.forEach((sensor1, i) => {
                activeSensors.forEach((sensor2, j) => {
                    const correlation = correlationMatrix[sensor1][sensor2];
                    matrixData.push({
                        x: j,
                        y: i,
                        v: correlation
                    });
                });
            });

            new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Correlation',
                        data: matrixData.map(d => ({
                            x: d.x,
                            y: d.y,
                            r: 20
                        })),
                        backgroundColor: matrixData.map(d => {
                            // Color scale: Blue (-1) -> Gray (0) -> Red (+1)
                            const val = d.v;
                            if (val > 0) {
                                const intensity = Math.floor(val * 255);
                                return `rgba(239, 68, 68, ${val})`;
                            } else if (val < 0) {
                                const intensity = Math.floor(Math.abs(val) * 255);
                                return `rgba(59, 130, 246, ${Math.abs(val)})`;
                            } else {
                                return 'rgba(107, 114, 128, 0.5)';
                            }
                        }),
                        pointStyle: 'rect'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'linear',
                            position: 'bottom',
                            min: -0.5,
                            max: activeSensors.length - 0.5,
                            ticks: {
                                color: '#9CA3AF',
                                callback: function(value) {
                                    return activeSensors[Math.round(value)]?.split('/').pop() || '';
                                }
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y: {
                            type: 'linear',
                            reverse: true,
                            min: -0.5,
                            max: activeSensors.length - 0.5,
                            ticks: {
                                color: '#9CA3AF',
                                callback: function(value) {
                                    return activeSensors[Math.round(value)]?.split('/').pop() || '';
                                }
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            enabled: true,
                            callbacks: {
                                label: function(context) {
                                    const i = Math.round(context.parsed.y);
                                    const j = Math.round(context.parsed.x);
                                    const correlation = correlationMatrix[activeSensors[i]][activeSensors[j]];
                                    return [
                                        `${activeSensors[i]}`,
                                        `vs`,
                                        `${activeSensors[j]}`,
                                        `r = ${correlation.toFixed(3)}`
                                    ];
                                }
                            }
                        }
                    }
                }
            });

            correlationHeatmapVisible = true;
        }

        // Add button to navigation for correlation heatmap
        function addCorrelationHeatmapButton() {
            const overlayButton = document.querySelector('button[onclick*="createOverlayChart"]');
            if (overlayButton && !document.getElementById('correlation-heatmap-btn')) {
                const heatmapButton = document.createElement('button');
                heatmapButton.id = 'correlation-heatmap-btn';
                heatmapButton.className = 'btn-primary';
                heatmapButton.textContent = 'Correlation Heatmap';
                heatmapButton.style.marginLeft = '12px';
                heatmapButton.onclick = createCorrelationHeatmap;
                overlayButton.parentElement.appendChild(heatmapButton);
            }
        }

        // Call this when overlay button is shown
        setTimeout(addCorrelationHeatmapButton, 1000);

        // Zero-Bus Configuration Functions
        function toggleConfig(protocol) {
            const panel = document.getElementById(`config-${protocol}`);
            const icon = document.getElementById(`toggle-${protocol}`);

            if (panel.classList.contains('expanded')) {
                panel.classList.remove('expanded');
                icon.classList.remove('expanded');
            } else {
                panel.classList.add('expanded');
                icon.classList.add('expanded');
            }
        }

        async function saveZeroBusConfig(protocol) {
            console.log(`saveZeroBusConfig called for protocol: ${protocol}`);

            const diagnostics = document.getElementById(`${protocol}-diagnostics`);
            if (!diagnostics) {
                console.error(`Diagnostics element not found: ${protocol}-diagnostics`);
                alert(`Error: Diagnostics panel not found for ${protocol}`);
                return;
            }

            diagnostics.innerHTML = '<div class="info">⏳ Saving configuration...</div>';

            try {
                // Parse target table (format: catalog.schema.table)
                const targetField = document.getElementById(`${protocol}-target`);
                const targetParts = targetField ? targetField.value.trim().split('.') : [];

                // Get selected sensors (if any were chosen via the modal)
                const selectedSensors = window[`${protocol}_selected_sensors`] || [];

                const config = {
                    workspace_host: document.getElementById(`${protocol}-workspace`).value.trim(),
                    zerobus_endpoint: document.getElementById(`${protocol}-zerobus`).value.trim(),
                    auth: {
                        client_id: document.getElementById(`${protocol}-client-id`).value.trim(),
                        client_secret: document.getElementById(`${protocol}-client-secret`).value.trim()
                    },
                    target: {
                        catalog: targetParts[0] || '',
                        schema: targetParts[1] || '',
                        table: targetParts[2] || ''
                    },
                    // Include sensor selection (empty array = all sensors)
                    selected_sensors: selectedSensors
                };

                console.log('Config object:', config);

                // Validate required fields
                if (!config.workspace_host || !config.zerobus_endpoint ||
                    !config.target.catalog || !config.target.schema || !config.target.table) {
                    diagnostics.innerHTML = '<div class="error">❌ Please fill in all required fields (workspace, endpoint, and table in format catalog.schema.table)</div>';
                    return;
                }

                console.log('Sending POST to /api/zerobus/config');

                // Send config to backend
                const response = await fetch('/api/zerobus/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        protocol: protocol,
                        config: config
                    })
                });

                console.log('Response status:', response.status);
                const data = await response.json();
                console.log('Response data:', data);

                if (data.success) {
                    diagnostics.innerHTML = `<div class="success">✅ Configuration saved successfully for ${protocol.toUpperCase()}<br><small>Config file: ${data.config_file}</small></div>`;
                } else {
                    diagnostics.innerHTML = `<div class="error">❌ Error: ${data.message}${data.detail ? '<br><small>' + data.detail + '</small>' : ''}</div>`;
                }
            } catch (error) {
                console.error('Error saving config:', error);
                diagnostics.innerHTML = `<div class="error">❌ Error saving configuration: ${error.message}</div>`;
            }
        }

        async function testZeroBusConnection(protocol) {
            const diagnostics = document.getElementById(`${protocol}-diagnostics`);
            diagnostics.innerHTML = '<div class="info">🔄 Testing Zero-Bus connection...</div>';

            // Parse target table (format: catalog.schema.table)
            const targetField = document.getElementById(`${protocol}-target`);
            const targetParts = targetField ? targetField.value.trim().split('.') : [];

            const config = {
                workspace_host: document.getElementById(`${protocol}-workspace`).value.trim(),
                zerobus_endpoint: document.getElementById(`${protocol}-zerobus`).value.trim(),
                auth: {
                    client_id: document.getElementById(`${protocol}-client-id`).value.trim(),
                    client_secret: document.getElementById(`${protocol}-client-secret`).value.trim()
                },
                target: {
                    catalog: targetParts[0] || '',
                    schema: targetParts[1] || '',
                    table: targetParts[2] || ''
                }
            };

            // Validate required fields
            if (!config.workspace_host || !config.zerobus_endpoint ||
                !config.target.catalog || !config.target.schema || !config.target.table) {
                diagnostics.innerHTML = '<div class="error">❌ Please fill in all required fields (workspace, endpoint, and table in format catalog.schema.table)</div>';
                return;
            }

            try {
                // Send test request to backend
                const response = await fetch('/api/zerobus/test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        protocol: protocol,
                        config: config
                    })
                });

                const data = await response.json();

                if (data.success) {
                    diagnostics.innerHTML = `<div class="success">✅ Connection successful!<br><strong>Table:</strong> ${data.table_name}<br><strong>Stream ID:</strong> ${data.stream_id}</div>`;
                } else {
                    diagnostics.innerHTML = `<div class="error">❌ Connection failed:<br>${data.message}${data.detail ? '<br><small>' + data.detail + '</small>' : ''}</div>`;
                }
            } catch (error) {
                console.error('Error testing connection:', error);
                diagnostics.innerHTML = `<div class="error">❌ Error testing connection: ${error.message}</div>`;
            }
        }

        async function startZeroBusService(protocol) {
            const btn = document.getElementById(`${protocol}-zerobus-btn`);
            const diagnostics = document.getElementById(`${protocol}-diagnostics`);

            // Check if already streaming (button shows "Stop Streaming")
            const isStreaming = btn.textContent.includes('Stop');

            if (isStreaming) {
                // Stop streaming
                btn.disabled = true;
                btn.textContent = '⏸ Stopping...';

                try {
                    const response = await fetch('/api/zerobus/stop', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ protocol: protocol })
                    });

                    const result = await response.json();

                    if (result.success) {
                        btn.textContent = '▶️ Start Streaming';
                        btn.className = 'btn-start-zerobus';
                        diagnostics.innerHTML = `<div class="success">${result.message}</div>`;
                    } else {
                        diagnostics.innerHTML = `<div class="error">❌ ${result.message}</div>`;
                        btn.textContent = '⏹ Stop Streaming';
                        btn.className = 'btn-stop-zerobus';
                    }
                } catch (error) {
                    diagnostics.innerHTML = `<div class="error">❌ Error stopping stream: ${error.message}</div>`;
                    btn.textContent = '⏹ Stop Streaming';
                    btn.className = 'btn-stop-zerobus';
                } finally {
                    btn.disabled = false;
                }
            } else {
                // Start streaming
                btn.disabled = true;
                btn.textContent = '⏳ Starting...';

                try {
                    const response = await fetch('/api/zerobus/start', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ protocol: protocol })
                    });

                    const result = await response.json();

                    if (result.success) {
                        btn.textContent = '⏹ Stop Streaming';
                        btn.className = 'btn-stop-zerobus';
                        diagnostics.innerHTML = `<div class="success">✅ ${result.message}<br>Data is being streamed to Zero-Bus every 5 seconds.</div>`;
                        // Update status periodically
                        updateStreamingStatus(protocol);
                    } else {
                        diagnostics.innerHTML = `<div class="error">❌ ${result.message}</div>`;
                        btn.textContent = '▶️ Start Streaming';
                        btn.className = 'btn-start-zerobus';
                    }
                } catch (error) {
                    diagnostics.innerHTML = `<div class="error">❌ Error starting stream: ${error.message}</div>`;
                    btn.textContent = '▶️ Start Streaming';
                    btn.className = 'btn-start-zerobus';
                } finally {
                    btn.disabled = false;
                }
            }
        }

        function updateStreamingStatus(protocol) {
            // Periodically check streaming status
            const interval = setInterval(async () => {
                const btn = document.getElementById(`${protocol}-zerobus-btn`);
                if (!btn || !btn.textContent.includes('Stop')) {
                    clearInterval(interval);
                    return;
                }

                try {
                    const response = await fetch('/api/zerobus/status');
                    const result = await response.json();

                    if (result.success && result.status[protocol]) {
                        if (!result.status[protocol].active) {
                            // Streaming stopped externally
                            btn.textContent = '▶️ Start Streaming';
                            btn.className = 'btn-start-zerobus';
                            clearInterval(interval);
                        }
                    }
                } catch (error) {
                    console.error('Error checking streaming status:', error);
                }
            }, 5000);
        }

        // Load saved Zero-Bus configuration for a protocol
        async function loadZeroBusConfig(protocol) {
            try {
                const response = await fetch('/api/zerobus/config/load', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ protocol: protocol })
                });

                const result = await response.json();

                if (result.success && result.config) {
                    const config = result.config;

                    // Populate form fields
                    const workspaceInput = document.getElementById(`${protocol}-workspace`);
                    const zerobusInput = document.getElementById(`${protocol}-zerobus`);
                    const clientIdInput = document.getElementById(`${protocol}-client-id`);
                    const clientSecretInput = document.getElementById(`${protocol}-client-secret`);
                    const targetInput = document.getElementById(`${protocol}-target`);

                    if (workspaceInput && config.workspace_host) {
                        workspaceInput.value = config.workspace_host;
                    }

                    if (zerobusInput && config.zerobus_endpoint) {
                        zerobusInput.value = config.zerobus_endpoint;
                    }

                    if (clientIdInput && config.auth) {
                        // Display the actual client ID (stored encrypted on server)
                        if (config.auth.client_id) {
                            clientIdInput.value = config.auth.client_id;
                        }
                    }

                    if (clientSecretInput && config.auth) {
                        // Display the actual client secret (stored encrypted on server)
                        if (config.auth.client_secret) {
                            clientSecretInput.value = config.auth.client_secret;
                        }
                    }

                    if (targetInput && config.target) {
                        // Reconstruct the target table from catalog.schema.table
                        const catalog = config.target.catalog || '';
                        const schema = config.target.schema || '';
                        const table = config.target.table || '';
                        if (catalog && schema && table) {
                            targetInput.value = `${catalog}.${schema}.${table}`;
                        }
                    }

                    console.log(`✅ Loaded saved configuration for ${protocol}`);
                } else {
                    console.log(`ℹ️ No saved configuration found for ${protocol}`);
                }
            } catch (error) {
                console.error(`Error loading configuration for ${protocol}:`, error);
            }
        }

        // Natural Language Chat
        const chatToggle = document.getElementById('nlp-chat-toggle');
        const chatPanel = document.getElementById('nlp-chat-panel');
        const chatClose = document.getElementById('chat-close');
        const chatMessages = document.getElementById('chat-messages');
        const chatInput = document.getElementById('chat-input');
        const chatSend = document.getElementById('chat-send');

        chatToggle.addEventListener('click', () => {
            chatPanel.classList.remove('hidden');
            chatInput.focus();
        });

        chatClose.addEventListener('click', () => {
            chatPanel.classList.add('hidden');
        });

        function addMessage(role, content, reasoning = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.textContent = role === 'user' ? '👤' : '🎛️';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';

            const bubble = document.createElement('div');
            bubble.className = 'message-bubble';
            // Use innerText instead of textContent to preserve line breaks
            bubble.style.whiteSpace = 'pre-wrap';
            bubble.textContent = content;

            contentDiv.appendChild(bubble);

            if (reasoning && role === 'agent') {
                const reasoningDiv = document.createElement('div');
                reasoningDiv.className = 'message-reasoning';
                reasoningDiv.textContent = `💭 ${reasoning}`;
                contentDiv.appendChild(reasoningDiv);
            }

            messageDiv.appendChild(avatar);
            messageDiv.appendChild(contentDiv);

            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function addTypingIndicator() {
            const indicatorDiv = document.createElement('div');
            indicatorDiv.className = 'message agent';
            indicatorDiv.id = 'typing-indicator';

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.textContent = '🎛️';

            const typingDiv = document.createElement('div');
            typingDiv.className = 'typing-indicator';
            typingDiv.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

            indicatorDiv.appendChild(avatar);
            indicatorDiv.appendChild(typingDiv);

            chatMessages.appendChild(indicatorDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function removeTypingIndicator() {
            const indicator = document.getElementById('typing-indicator');
            if (indicator) {
                indicator.remove();
            }
        }

        function sendMessage() {
            const text = chatInput.value.trim();
            if (!text) return;

            console.log('Sending NLP command:', text);

            // Display user message
            addMessage('user', text);
            chatInput.value = '';

            // Add to conversation history
            conversationHistory.push({
                role: 'user',
                content: text
            });

            // Send to WebSocket
            if (ws && ws.readyState === WebSocket.OPEN) {
                const message = {
                    type: 'nlp_command',
                    text: text,
                    history: conversationHistory.slice(-10)  // Last 10 messages
                };
                console.log('WebSocket sending:', message);
                ws.send(JSON.stringify(message));

                // Show typing indicator
                addTypingIndicator();
            } else {
                console.error('WebSocket not connected, state:', ws?.readyState);
                addMessage('agent', '❌ WebSocket connection not available. Please refresh the page.');
            }
        }

        chatSend.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Load sensors
        async function loadSensors() {
            try {
                const response = await fetch('/api/sensors');
                const industries = await response.json();

                const sensorBrowser = document.getElementById('sensor-browser');
                sensorBrowser.innerHTML = '';

                // Render each industry accordion
                Object.values(industries).forEach(industry => {
                    const accordionDiv = document.createElement('div');
                    accordionDiv.className = 'industry-accordion';

                    // Industry header
                    const headerDiv = document.createElement('div');
                    headerDiv.className = 'industry-header';
                    headerDiv.innerHTML = `
                        <div class="industry-header-left">
                            <span class="industry-title">${industry.display_name}</span>
                            <span class="industry-count">${industry.sensor_count} sensors</span>
                        </div>
                        <span class="industry-chevron">▶</span>
                    `;

                    // Sensors container
                    const sensorsDiv = document.createElement('div');
                    sensorsDiv.className = 'industry-sensors';

                    // Render sensors
                    industry.sensors.forEach(sensor => {
                        const sensorItem = document.createElement('div');
                        sensorItem.className = 'sensor-item';

                        // Protocol badges HTML
                        const protocolBadgesHTML = sensor.protocols.map(proto =>
                            `<span class="protocol-badge-mini ${proto}">${proto}</span>`
                        ).join('');

                        sensorItem.innerHTML = `
                            <div class="sensor-info">
                                <div class="sensor-name">${sensor.name}</div>
                                <div class="sensor-meta">
                                    <span class="sensor-type">${sensor.type}</span>
                                    <div class="protocol-badges">
                                        ${protocolBadgesHTML}
                                    </div>
                                </div>
                            </div>
                            <span class="sensor-add">+</span>
                        `;

                        sensorItem.onclick = (event) => {
                            // Check for Ctrl/Cmd key for multi-selection
                            if (event.ctrlKey || event.metaKey) {
                                event.stopPropagation();
                                toggleSensorSelection(sensor.path, sensor, sensorItem);
                            } else {
                                // Normal single chart creation
                                if (!charts[sensor.path]) {
                                    createChart(sensor.path, sensor);
                                }
                            }
                        };

                        sensorsDiv.appendChild(sensorItem);
                    });

                    // Toggle accordion
                    headerDiv.onclick = () => {
                        const isExpanded = sensorsDiv.classList.contains('expanded');
                        const chevron = headerDiv.querySelector('.industry-chevron');

                        if (isExpanded) {
                            sensorsDiv.classList.remove('expanded');
                            headerDiv.classList.remove('active');
                            chevron.classList.remove('expanded');
                        } else {
                            sensorsDiv.classList.add('expanded');
                            headerDiv.classList.add('active');
                            chevron.classList.add('expanded');
                        }
                    };

                    accordionDiv.appendChild(headerDiv);
                    accordionDiv.appendChild(sensorsDiv);
                    sensorBrowser.appendChild(accordionDiv);
                });
            } catch (error) {
                console.error('Error loading sensors:', error);
            }
        }

        // Initialize Zero-Bus streaming button states
        async function initZeroBusButtons() {
            try {
                const response = await fetch('/api/zerobus/status');
                const result = await response.json();

                if (result.success && result.status) {
                    // Update button states for each protocol
                    ['opcua', 'mqtt', 'modbus'].forEach(protocol => {
                        const status = result.status[protocol];
                        const btn = document.getElementById(`${protocol}-zerobus-btn`);

                        if (btn && status) {
                            if (status.active) {
                                // Streaming is active
                                btn.textContent = '⏹ Stop Streaming';
                                btn.className = 'btn-stop-zerobus';
                                // Start periodic status updates
                                updateStreamingStatus(protocol);
                            } else {
                                // Streaming is not active
                                btn.textContent = '▶️ Start Streaming';
                                btn.className = 'btn-start-zerobus';
                            }
                        }
                    });
                }
            } catch (error) {
                console.error('Error initializing ZeroBus button states:', error);
            }
        }

        // Initialize
        connectWebSocket();
        loadSensors();

        // Load saved Zero-Bus configurations for all protocols
        loadZeroBusConfig('opcua');
        loadZeroBusConfig('mqtt');
        loadZeroBusConfig('modbus');

        // Initialize ZeroBus button states based on current streaming status
        initZeroBusButtons();

        // Add some default charts
        setTimeout(() => {
            // These will be created once sensors are loaded
            const defaultSensors = [
                'mining/crusher_1_motor_power',
                'utilities/grid_main_frequency'
            ];
            // Will auto-create once sensor data is available
        }, 1000);

        // OPC-UA Browser functionality
        const opcuaBrowserToggle = document.getElementById('opcua-browser-toggle');
        const opcuaBrowserPanel = document.getElementById('opcua-browser-panel');
        const opcuaBrowserClose = document.getElementById('opcua-browser-close');
        const opcuaTreeContainer = document.getElementById('opcua-tree-container');
        const opcuaSearchInput = document.getElementById('opcua-search-input');

        let opcuaHierarchyData = null;
        let opcuaUpdateInterval = null;

        // Toggle OPC-UA browser panel
        opcuaBrowserToggle.addEventListener('click', () => {
            opcuaBrowserPanel.classList.remove('hidden');
            if (!opcuaHierarchyData) {
                loadOpcuaHierarchy();
            }
            // Start auto-refresh (500ms for smoother updates)
            if (!opcuaUpdateInterval) {
                opcuaUpdateInterval = setInterval(updateOpcuaValues, 500);
            }
        });

        opcuaBrowserClose.addEventListener('click', () => {
            opcuaBrowserPanel.classList.add('hidden');
            // Stop auto-refresh when closed
            if (opcuaUpdateInterval) {
                clearInterval(opcuaUpdateInterval);
                opcuaUpdateInterval = null;
            }
        });

        // Auto-close floating panels when user clicks on config inputs
        // This prevents panels from overlapping Zero-Bus config forms
        document.addEventListener('focusin', (e) => {
            const target = e.target;
            // Check if the focused element is an input or textarea in a config section
            if ((target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') &&
                target.closest('.config-section, .zerobus-section')) {
                // Close OPC-UA browser
                opcuaBrowserPanel.classList.add('hidden');
                if (opcuaUpdateInterval) {
                    clearInterval(opcuaUpdateInterval);
                    opcuaUpdateInterval = null;
                }
                // Close NLP chat
                chatPanel.classList.add('hidden');
            }
        });

        // Search functionality with fuzzy matching
        opcuaSearchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            filterOpcuaTree(searchTerm);
        });

        // Fuzzy search aliases - common full words map to abbreviations
        const searchAliases = {
            'temperature': 'temp',
            'pressure': 'press',
            'vibration': 'vib',
            'position': 'pos',
            'current': 'curr',
            'voltage': 'volt',
            'frequency': 'freq',
            'humidity': 'hum',
            'conveyor': 'conv'
        };

        function expandSearchTerm(term) {
            // Check if the search term matches any alias
            const lowerTerm = term.toLowerCase();
            for (const [fullWord, abbrev] of Object.entries(searchAliases)) {
                if (lowerTerm.includes(fullWord)) {
                    // Return both the original and abbreviated version
                    return [term, term.replace(new RegExp(fullWord, 'gi'), abbrev)];
                }
            }
            return [term];
        }

        function filterOpcuaTree(searchTerm) {
            const allNodes = document.querySelectorAll('.tree-node');
            const allContainers = document.querySelectorAll('.tree-children');
            const allHeaders = document.querySelectorAll('.tree-node-header');

            if (!searchTerm) {
                // Show all nodes and reset expansion
                allNodes.forEach(node => node.style.display = '');
                allContainers.forEach(container => container.style.display = '');
                allHeaders.forEach(header => header.style.display = '');
                return;
            }

            // First, hide everything
            allNodes.forEach(node => node.style.display = 'none');

            // Expand search term to include aliases
            const searchTerms = expandSearchTerm(searchTerm);

            // Find all matching nodes
            const matchingNodes = [];
            allNodes.forEach(node => {
                const header = node.querySelector('.tree-node-header');
                const label = header ? header.querySelector('.tree-label') : null;
                const labelText = label ? label.textContent.toLowerCase() : '';

                // Check if any of the search terms match
                const matches = searchTerms.some(term => labelText.includes(term.toLowerCase()));

                if (matches) {
                    matchingNodes.push(node);
                    // Show this node
                    node.style.display = '';

                    // Show and expand all parent nodes
                    let parent = node.parentElement;
                    while (parent) {
                        if (parent.classList.contains('tree-children')) {
                            parent.style.display = '';
                            parent.classList.add('expanded');

                            // Find and show the parent node
                            const parentNode = parent.closest('.tree-node');
                            if (parentNode) {
                                parentNode.style.display = '';
                            }

                            // Expand the header
                            const header = parent.previousElementSibling;
                            if (header && header.classList.contains('tree-node-header')) {
                                header.style.display = '';
                                header.classList.add('active');
                                const chevron = header.querySelector('.tree-chevron');
                                if (chevron) chevron.classList.add('expanded');
                            }
                        }
                        parent = parent.parentElement;
                    }
                }
            });

            console.log(`Search "${searchTerm}" found ${matchingNodes.length} matches`);
        }

        async function loadOpcuaHierarchy() {
            try {
                opcuaTreeContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #6B7280;">Loading OPC-UA hierarchy...</div>';

                const response = await fetch('/api/opcua/hierarchy');
                opcuaHierarchyData = await response.json();

                renderOpcuaTree();
            } catch (error) {
                console.error('Error loading OPC-UA hierarchy:', error);
                opcuaTreeContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #DC2626;">Failed to load hierarchy. Please try again.</div>';
            }
        }

        async function updateOpcuaValues() {
            // Fetch fresh data and update only the values
            try {
                const response = await fetch('/api/opcua/hierarchy');
                const newData = await response.json();
                updateNodeValues(newData);
            } catch (error) {
                console.error('Error updating OPC-UA values:', error);
            }
        }

        function updateNodeValues(data) {
            // Update sensor values without re-rendering entire tree
            const updateNode = (node) => {
                if (node.type === 'sensor' && node.path) {
                    const valueElement = document.querySelector(`[data-sensor-path="${node.path}"] .tree-value`);
                    const qualityElement = document.querySelector(`[data-sensor-path="${node.path}"] .tree-quality`);

                    if (valueElement && node.value !== undefined) {
                        const oldValue = valueElement.textContent;
                        const newValue = node.value.toFixed(2);

                        // Only flash if value actually changed
                        if (oldValue !== newValue) {
                            valueElement.textContent = newValue;

                            // Add flash animation
                            valueElement.classList.add('updated');

                            // Remove the class after animation completes
                            setTimeout(() => {
                                valueElement.classList.remove('updated');
                            }, 500);
                        }
                    }

                    if (qualityElement && node.quality) {
                        // Update quality badge
                        qualityElement.className = 'tree-quality';
                        if (node.forced) {
                            qualityElement.classList.add('forced');
                            qualityElement.textContent = 'FORCED';
                        } else if (node.quality.toLowerCase().includes('good')) {
                            qualityElement.classList.add('good');
                            qualityElement.textContent = 'Good';
                        } else if (node.quality.toLowerCase().includes('uncertain')) {
                            qualityElement.classList.add('uncertain');
                            qualityElement.textContent = 'Uncertain';
                        } else if (node.quality.toLowerCase().includes('bad')) {
                            qualityElement.classList.add('bad');
                            qualityElement.textContent = node.quality;
                        }
                    }
                }

                if (node.children) {
                    node.children.forEach(updateNode);
                }
            };

            updateNode(data);
        }

        function renderOpcuaTree() {
            if (!opcuaHierarchyData) return;

            opcuaTreeContainer.innerHTML = '';

            // Render root
            const rootNode = createTreeNode({
                name: opcuaHierarchyData.root,
                type: 'root',
                children: opcuaHierarchyData.children
            }, 0);

            opcuaTreeContainer.appendChild(rootNode);
        }

        function createTreeNode(node, depth) {
            const nodeDiv = document.createElement('div');
            nodeDiv.className = 'tree-node';

            const hasChildren = node.children && node.children.length > 0;
            const hasProperties = node.properties && Object.keys(node.properties).length > 0;

            // Create header
            const header = document.createElement('div');
            header.className = 'tree-node-header';

            // Chevron
            const chevron = document.createElement('span');
            chevron.className = hasChildren || hasProperties ? 'tree-chevron' : 'tree-chevron leaf';
            chevron.textContent = '▶';
            header.appendChild(chevron);

            // Icon based on type
            const icon = document.createElement('span');
            icon.className = 'tree-icon';
            if (node.type === 'root' || node.type === 'folder') {
                icon.textContent = '📁';
            } else if (node.type === 'plc') {
                icon.textContent = '⚙️';
            } else if (node.type === 'industry') {
                icon.textContent = '🏭';
            } else if (node.type === 'sensor') {
                icon.textContent = '📊';
            } else {
                icon.textContent = '📄';
            }
            header.appendChild(icon);

            // Label
            const label = document.createElement('span');
            label.className = 'tree-label';
            label.textContent = node.name;
            header.appendChild(label);

            // For sensors, show value and quality
            if (node.type === 'sensor') {
                header.setAttribute('data-sensor-path', node.path);

                const value = document.createElement('span');
                value.className = 'tree-value';
                value.textContent = node.value !== undefined ? node.value.toFixed(2) : '--';
                header.appendChild(value);

                const unit = document.createElement('span');
                unit.className = 'tree-unit';
                unit.textContent = node.unit || '';
                header.appendChild(unit);

                const quality = document.createElement('span');
                quality.className = 'tree-quality';
                if (node.forced) {
                    quality.classList.add('forced');
                    quality.textContent = 'FORCED';
                } else if (node.quality && node.quality.toLowerCase().includes('good')) {
                    quality.classList.add('good');
                    quality.textContent = 'Good';
                } else if (node.quality && node.quality.toLowerCase().includes('uncertain')) {
                    quality.classList.add('uncertain');
                    quality.textContent = 'Uncertain';
                } else if (node.quality && node.quality.toLowerCase().includes('bad')) {
                    quality.classList.add('bad');
                    quality.textContent = node.quality;
                } else {
                    quality.classList.add('good');
                    quality.textContent = 'Good';
                }
                header.appendChild(quality);
            }

            nodeDiv.appendChild(header);

            // Create children container
            if (hasChildren || hasProperties) {
                const childrenDiv = document.createElement('div');
                childrenDiv.className = 'tree-children';

                // Add properties if present
                if (hasProperties) {
                    const propsDiv = document.createElement('div');
                    propsDiv.className = 'tree-properties';

                    Object.entries(node.properties).forEach(([key, value]) => {
                        const propDiv = document.createElement('div');
                        propDiv.className = 'tree-property';

                        const propName = document.createElement('span');
                        propName.className = 'tree-property-name';
                        propName.textContent = key + ':';
                        propDiv.appendChild(propName);

                        const propValue = document.createElement('span');
                        propValue.className = 'tree-property-value';
                        propValue.textContent = value;
                        propDiv.appendChild(propValue);

                        propsDiv.appendChild(propDiv);
                    });

                    childrenDiv.appendChild(propsDiv);
                }

                // Add child nodes
                if (hasChildren) {
                    node.children.forEach(child => {
                        const childNode = createTreeNode(child, depth + 1);
                        childrenDiv.appendChild(childNode);
                    });
                }

                nodeDiv.appendChild(childrenDiv);

                // Toggle functionality
                header.addEventListener('click', () => {
                    const isExpanded = childrenDiv.classList.contains('expanded');

                    if (isExpanded) {
                        childrenDiv.classList.remove('expanded');
                        header.classList.remove('active');
                        chevron.classList.remove('expanded');
                    } else {
                        childrenDiv.classList.add('expanded');
                        header.classList.add('active');
                        chevron.classList.add('expanded');
                    }
                });
            }

            return nodeDiv;
        }

        // ==================== Sensor Selection ====================
        let sensorSelectionState = {
            currentProtocol: null,
            allSensors: [],
            selectedSensors: new Set(),
            // Filters track which items are ENABLED (checked = show, unchecked = hide)
            enabledFilters: {
                industries: new Set(),  // Empty = all enabled
                sensorTypes: new Set(), // Empty = all enabled
                plcs: new Set()         // Empty = all enabled
            }
        };

        async function openSensorSelector(protocol) {
            sensorSelectionState.currentProtocol = protocol;
            document.getElementById('sensor-modal-protocol').textContent = protocol.toUpperCase();

            // Load sensors from API
            try {
                const response = await fetch('/api/sensors');
                const industries = await response.json();

                // Flatten sensors from all industries
                sensorSelectionState.allSensors = [];
                for (const industryName in industries) {
                    const industry = industries[industryName];
                    industry.sensors.forEach(sensor => {
                        sensor.industryDisplay = industry.display_name;
                        // Use actual PLC vendor and model if available
                        if (sensor.plc_vendor && sensor.plc_model) {
                            sensor.plc = `${sensor.plc_vendor} ${sensor.plc_model}`;
                        } else {
                            sensor.plc = 'Unknown PLC';
                        }
                        sensorSelectionState.allSensors.push(sensor);
                    });
                }

                // Initialize with NO sensors selected (empty set)
                sensorSelectionState.selectedSensors = new Set();

                // Build filter options
                buildFilterOptions();

                // Render sensor list
                renderSensorList();

                // Show modal
                document.getElementById('sensor-modal').classList.add('active');
            } catch (error) {
                console.error('Error loading sensors:', error);
                alert('Failed to load sensors');
            }
        }

        function closeSensorSelector() {
            document.getElementById('sensor-modal').classList.remove('active');
        }

        function buildFilterOptions() {
            const industries = new Set();
            const sensorTypes = new Set();
            const plcs = new Set();

            sensorSelectionState.allSensors.forEach(sensor => {
                industries.add(sensor.industryDisplay);
                sensorTypes.add(sensor.type);
                plcs.add(sensor.plc);
            });

            // Initialize enabledFilters as empty (checkboxes start unchecked)
            sensorSelectionState.enabledFilters.industries = new Set();
            sensorSelectionState.enabledFilters.sensorTypes = new Set();
            sensorSelectionState.enabledFilters.plcs = new Set();

            // Industry filters
            const industryContainer = document.getElementById('industry-filter-options');
            industryContainer.innerHTML = '';
            Array.from(industries).sort().forEach(industry => {
                const option = createFilterOption('industry', industry);
                industryContainer.appendChild(option);
            });

            // Sensor type filters
            const typeContainer = document.getElementById('sensor-type-filter-options');
            typeContainer.innerHTML = '';
            Array.from(sensorTypes).sort().forEach(type => {
                const option = createFilterOption('type', type);
                typeContainer.appendChild(option);
            });

            // PLC filters
            const plcContainer = document.getElementById('plc-filter-options');
            plcContainer.innerHTML = '';
            Array.from(plcs).sort().forEach(plc => {
                // PLC names are already formatted (e.g., "rockwell ControlLogix 5580")
                const option = createFilterOption('plc', plc);
                plcContainer.appendChild(option);
            });
        }

        function createFilterOption(filterType, displayName, value = null) {
            const actualValue = value || displayName;
            const div = document.createElement('div');
            div.className = 'sensor-filter-option';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = false;
            checkbox.id = `filter-${filterType}-${actualValue}`;
            checkbox.onchange = () => handleFilterChange(filterType, actualValue, checkbox.checked);

            const label = document.createElement('label');
            label.htmlFor = checkbox.id;
            label.textContent = displayName;

            div.appendChild(checkbox);
            div.appendChild(label);

            return div;
        }

        function handleFilterChange(filterType, value, checked) {
            // CORRECTED LOGIC: Checked = add to enabledFilters (show), Unchecked = remove (hide)
            if (filterType === 'industry') {
                if (checked) {
                    sensorSelectionState.enabledFilters.industries.add(value);
                } else {
                    sensorSelectionState.enabledFilters.industries.delete(value);
                }
            } else if (filterType === 'type') {
                if (checked) {
                    sensorSelectionState.enabledFilters.sensorTypes.add(value);
                } else {
                    sensorSelectionState.enabledFilters.sensorTypes.delete(value);
                }
            } else if (filterType === 'plc') {
                if (checked) {
                    sensorSelectionState.enabledFilters.plcs.add(value);
                } else {
                    sensorSelectionState.enabledFilters.plcs.delete(value);
                }
            }

            renderSensorList();
        }

        function getFilteredSensors() {
            return sensorSelectionState.allSensors.filter(sensor => {
                // CORRECTED LOGIC: Empty set = show all, otherwise check if item IS IN enabledFilters

                // Industry filter: if set is not empty, sensor must be in the enabled set
                if (sensorSelectionState.enabledFilters.industries.size > 0 &&
                    !sensorSelectionState.enabledFilters.industries.has(sensor.industryDisplay)) {
                    return false;
                }

                // Sensor type filter
                if (sensorSelectionState.enabledFilters.sensorTypes.size > 0 &&
                    !sensorSelectionState.enabledFilters.sensorTypes.has(sensor.type)) {
                    return false;
                }

                // PLC filter
                if (sensorSelectionState.enabledFilters.plcs.size > 0 &&
                    !sensorSelectionState.enabledFilters.plcs.has(sensor.plc)) {
                    return false;
                }

                return true;
            });
        }

        function renderSensorList() {
            const filteredSensors = getFilteredSensors();
            const container = document.getElementById('sensor-items-grid');
            container.innerHTML = '';

            filteredSensors.forEach(sensor => {
                const item = createSensorItem(sensor);
                container.appendChild(item);
            });

            // Update counts
            document.getElementById('filtered-sensor-count').textContent = filteredSensors.length;
            updateSelectedCount();
        }

        function createSensorItem(sensor) {
            const div = document.createElement('div');
            div.className = 'sensor-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = sensorSelectionState.selectedSensors.has(sensor.path);
            checkbox.id = `sensor-${sensor.path.replace(/[\\/\\.]/g, '-')}`;
            checkbox.onchange = () => handleSensorSelection(sensor.path, checkbox.checked);

            const label = document.createElement('label');
            label.className = 'sensor-item-label';
            label.htmlFor = checkbox.id;
            label.textContent = sensor.name;

            const badge = document.createElement('span');
            badge.className = 'sensor-item-badge';
            badge.textContent = sensor.unit;

            div.appendChild(checkbox);
            div.appendChild(label);
            div.appendChild(badge);

            return div;
        }

        function handleSensorSelection(sensorPath, selected) {
            if (selected) {
                sensorSelectionState.selectedSensors.add(sensorPath);
            } else {
                sensorSelectionState.selectedSensors.delete(sensorPath);
            }
            updateSelectedCount();
        }

        function updateSelectedCount() {
            document.getElementById('selected-sensor-count').textContent =
                sensorSelectionState.selectedSensors.size;
        }

        function selectAllFilteredSensors() {
            const filteredSensors = getFilteredSensors();
            filteredSensors.forEach(sensor => {
                sensorSelectionState.selectedSensors.add(sensor.path);
            });
            renderSensorList();
        }

        function clearAllSensors() {
            sensorSelectionState.selectedSensors.clear();
            renderSensorList();
        }

        function applySensorSelection() {
            const protocol = sensorSelectionState.currentProtocol;
            const selectedCount = sensorSelectionState.selectedSensors.size;
            const totalCount = sensorSelectionState.allSensors.length;

            // Update summary text
            const summaryDiv = document.getElementById(`${protocol}-sensor-summary`);
            if (selectedCount === 0) {
                summaryDiv.textContent = 'No sensors selected';
                summaryDiv.style.color = '#EF4444';
            } else if (selectedCount === totalCount) {
                summaryDiv.textContent = `All sensors selected (${totalCount} total)`;
                summaryDiv.style.color = '#6B7280';
            } else {
                summaryDiv.textContent = `${selectedCount} of ${totalCount} sensors selected`;
                summaryDiv.style.color = '#059669';
            }

            // Store selection for later use (when starting Zero-Bus streaming)
            window[`${protocol}_selected_sensors`] = Array.from(sensorSelectionState.selectedSensors);

            closeSensorSelector();
        }

        // Close modal on background click
        document.getElementById('sensor-modal').addEventListener('click', (e) => {
            if (e.target.id === 'sensor-modal') {
                closeSensorSelector();
            }
        });
    </script>
</body>
</html>"""


def get_main_page_html() -> str:
    """Return the complete HTML page by combining all sections."""
    return (
        get_head_html()
        + "\n"
        + get_styles_html()
        + "\n"
        + get_body_html()
        + "\n"
        + get_scripts_html()
    )
