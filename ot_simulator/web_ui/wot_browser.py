"""W3C WoT Thing Description Browser.

This module provides a beautiful, interactive UI for exploring Thing Descriptions
with features like:
- Searchable/filterable property list
- Semantic type filtering (SAREF, SOSA)
- Industry filtering
- Property details with ontology information
- Statistics and summary views
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import web

if TYPE_CHECKING:
    from ot_simulator.simulator_manager import SimulatorManager

logger = logging.getLogger("ot_simulator.wot_browser")


async def handle_wot_browser(request: web.Request) -> web.Response:
    """Serve the WoT Thing Description browser page."""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>W3C WoT Thing Description Browser - Databricks OT Simulator</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --navy: #1B3139;
            --cyan: #00A8E1;
            --lava: #FF3621;
            --white: #FFFFFF;
            --light-gray: #F5F5F5;
            --gray: #E0E0E0;
            --dark-gray: #666;
            --success: #4CAF50;
            --warning: #FF9800;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--navy) 0%, #2A4A54 100%);
            color: var(--navy);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: var(--white);
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(90deg, var(--lava) 0%, #FF6B57 100%);
            color: var(--white);
            padding: 30px 40px;
            position: relative;
            overflow: hidden;
        }

        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -5%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            border-radius: 50%;
        }

        .header h1 {
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 8px;
            position: relative;
            z-index: 1;
        }

        .header .subtitle {
            font-size: 16px;
            opacity: 0.95;
            position: relative;
            z-index: 1;
        }

        .stats-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px 40px;
            background: var(--light-gray);
            border-bottom: 1px solid var(--gray);
        }

        .stat-card {
            background: var(--white);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid var(--cyan);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .stat-card.lava {
            border-left-color: var(--lava);
        }

        .stat-card.success {
            border-left-color: var(--success);
        }

        .stat-label {
            font-size: 12px;
            color: var(--dark-gray);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: var(--navy);
        }

        .controls {
            padding: 30px 40px;
            background: var(--white);
            border-bottom: 1px solid var(--gray);
        }

        .search-row {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .search-box {
            flex: 1;
            min-width: 250px;
        }

        .search-box input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid var(--gray);
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.2s;
        }

        .search-box input:focus {
            outline: none;
            border-color: var(--cyan);
            box-shadow: 0 0 0 3px rgba(0, 168, 225, 0.1);
        }

        .filter-row {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }

        .filter-select {
            padding: 10px 16px;
            border: 2px solid var(--gray);
            border-radius: 6px;
            font-size: 14px;
            background: var(--white);
            cursor: pointer;
            transition: all 0.2s;
        }

        .filter-select:focus {
            outline: none;
            border-color: var(--cyan);
        }

        .results-info {
            padding: 20px 40px;
            background: var(--light-gray);
            font-size: 14px;
            color: var(--dark-gray);
            border-bottom: 1px solid var(--gray);
        }

        .properties-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
            padding: 30px 40px;
            max-height: 800px;
            overflow-y: auto;
        }

        .property-card {
            background: var(--white);
            border: 1px solid var(--gray);
            border-radius: 8px;
            padding: 20px;
            transition: all 0.2s;
            cursor: pointer;
        }

        .property-card:hover {
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            transform: translateY(-2px);
            border-color: var(--cyan);
        }

        .property-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 12px;
        }

        .property-name {
            font-size: 16px;
            font-weight: 600;
            color: var(--navy);
            margin-bottom: 4px;
        }

        .property-title {
            font-size: 13px;
            color: var(--dark-gray);
        }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .badge.saref {
            background: #E3F2FD;
            color: #1976D2;
        }

        .badge.sosa {
            background: #F3E5F5;
            color: #7B1FA2;
        }

        .badge.opcua {
            background: #FFF3E0;
            color: #E65100;
        }

        .badge.industry {
            background: var(--light-gray);
            color: var(--navy);
            margin-top: 4px;
        }

        .property-details {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 8px;
            font-size: 13px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--gray);
        }

        .detail-label {
            color: var(--dark-gray);
            font-weight: 600;
        }

        .detail-value {
            color: var(--navy);
            word-break: break-all;
        }

        .unit-uri {
            color: var(--cyan);
            text-decoration: none;
            font-size: 12px;
        }

        .unit-uri:hover {
            text-decoration: underline;
        }

        .loading {
            text-align: center;
            padding: 60px;
            color: var(--dark-gray);
        }

        .spinner {
            border: 3px solid var(--gray);
            border-top: 3px solid var(--cyan);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .no-results {
            text-align: center;
            padding: 60px;
            color: var(--dark-gray);
        }

        .back-button {
            display: inline-block;
            padding: 10px 20px;
            background: var(--navy);
            color: var(--white);
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
            margin-top: 10px;
        }

        .back-button:hover {
            background: var(--cyan);
            transform: translateX(-4px);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 W3C WoT Thing Description Browser</h1>
            <div class="subtitle">Explore 379 industrial sensors with semantic metadata</div>
            <a href="/" class="back-button">← Back to Dashboard</a>
        </div>

        <div class="stats-bar" id="stats">
            <div class="stat-card">
                <div class="stat-label">Total Properties</div>
                <div class="stat-value" id="totalProperties">-</div>
            </div>
            <div class="stat-card lava">
                <div class="stat-label">Semantic Types</div>
                <div class="stat-value" id="semanticTypes">-</div>
            </div>
            <div class="stat-card success">
                <div class="stat-label">Industries</div>
                <div class="stat-value" id="industries">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">W3C Compliant</div>
                <div class="stat-value">✓</div>
            </div>
        </div>

        <div class="controls">
            <div class="search-row">
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="🔍 Search properties by name...">
                </div>
            </div>
            <div class="filter-row">
                <select class="filter-select" id="semanticFilter">
                    <option value="">All Semantic Types</option>
                </select>
                <select class="filter-select" id="industryFilter">
                    <option value="">All Industries</option>
                </select>
                <select class="filter-select" id="unitFilter">
                    <option value="">All Units</option>
                </select>
            </div>
        </div>

        <div class="results-info" id="resultsInfo">
            Loading Thing Description...
        </div>

        <div id="content">
            <div class="loading">
                <div class="spinner"></div>
                <div>Fetching Thing Description from simulator...</div>
            </div>
        </div>
    </div>

    <script>
        let thingDescription = null;
        let properties = [];
        let filteredProperties = [];

        async function fetchThingDescription() {
            try {
                const response = await fetch('/api/opcua/thing-description');
                thingDescription = await response.json();
                processThingDescription();
                renderStats();
                renderProperties();
                updateResultsInfo();
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="no-results">
                        <h2>Failed to load Thing Description</h2>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        }

        function processThingDescription() {
            properties = [];
            const props = thingDescription.properties || {};

            for (const [name, prop] of Object.entries(props)) {
                const semanticTypes = prop['@type'] || [];
                const semanticType = Array.isArray(semanticTypes) ? semanticTypes[0] : semanticTypes;

                properties.push({
                    name: name,
                    title: prop.title || name,
                    description: prop.description || '',
                    semanticType: semanticType,
                    unit: prop.unit || '',
                    unitUri: prop['qudt:unit'] || '',
                    industry: prop['ex:industry'] || '',
                    minimum: prop.minimum,
                    maximum: prop.maximum,
                    nodeId: prop.forms?.[0]?.['opcua:nodeId'] || '',
                    browsePath: prop.forms?.[0]?.['opcua:browsePath'] || ''
                });
            }

            filteredProperties = [...properties];
            populateFilters();
        }

        function populateFilters() {
            // Semantic types
            const semanticTypes = [...new Set(properties.map(p => p.semanticType).filter(Boolean))].sort();
            const semanticFilter = document.getElementById('semanticFilter');
            semanticTypes.forEach(type => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type;
                semanticFilter.appendChild(option);
            });

            // Industries
            const industries = [...new Set(properties.map(p => p.industry).filter(Boolean))].sort();
            const industryFilter = document.getElementById('industryFilter');
            industries.forEach(ind => {
                const option = document.createElement('option');
                option.value = ind;
                option.textContent = ind.replace(/_/g, ' ').toUpperCase();
                industryFilter.appendChild(option);
            });

            // Units
            const units = [...new Set(properties.map(p => p.unit).filter(Boolean))].sort();
            const unitFilter = document.getElementById('unitFilter');
            units.forEach(unit => {
                const option = document.createElement('option');
                option.value = unit;
                option.textContent = unit;
                unitFilter.appendChild(option);
            });
        }

        function renderStats() {
            const semanticTypes = new Set(properties.map(p => p.semanticType).filter(Boolean));
            const industries = new Set(properties.map(p => p.industry).filter(Boolean));

            document.getElementById('totalProperties').textContent = properties.length;
            document.getElementById('semanticTypes').textContent = semanticTypes.size;
            document.getElementById('industries').textContent = industries.size;
        }

        function renderProperties() {
            const content = document.getElementById('content');

            if (filteredProperties.length === 0) {
                content.innerHTML = `
                    <div class="no-results">
                        <h2>No properties match your filters</h2>
                        <p>Try adjusting your search or filters</p>
                    </div>
                `;
                return;
            }

            const grid = document.createElement('div');
            grid.className = 'properties-grid';

            filteredProperties.forEach(prop => {
                const card = createPropertyCard(prop);
                grid.appendChild(card);
            });

            content.innerHTML = '';
            content.appendChild(grid);
        }

        function createPropertyCard(prop) {
            const card = document.createElement('div');
            card.className = 'property-card';

            const semanticBadge = prop.semanticType ?
                `<span class="badge ${prop.semanticType.startsWith('saref:') ? 'saref' : 'sosa'}">${prop.semanticType}</span>` : '';

            const industryBadge = prop.industry ?
                `<span class="badge industry">${prop.industry.replace(/_/g, ' ')}</span>` : '';

            const rangeText = (prop.minimum !== undefined && prop.maximum !== undefined) ?
                `${prop.minimum} - ${prop.maximum}` : '-';

            card.innerHTML = `
                <div class="property-header">
                    <div>
                        <div class="property-name">${prop.name}</div>
                        <div class="property-title">${prop.title}</div>
                    </div>
                    ${semanticBadge}
                </div>
                ${industryBadge}
                <div class="property-details">
                    <span class="detail-label">Unit:</span>
                    <span class="detail-value">${prop.unit || '-'}
                        ${prop.unitUri ? `<br><a href="${prop.unitUri}" target="_blank" class="unit-uri">${prop.unitUri}</a>` : ''}
                    </span>
                    <span class="detail-label">Range:</span>
                    <span class="detail-value">${rangeText}</span>
                    <span class="detail-label">Node ID:</span>
                    <span class="detail-value">${prop.nodeId || '-'}</span>
                </div>
            `;

            return card;
        }

        function applyFilters() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const semanticType = document.getElementById('semanticFilter').value;
            const industry = document.getElementById('industryFilter').value;
            const unit = document.getElementById('unitFilter').value;

            filteredProperties = properties.filter(prop => {
                const matchesSearch = !searchTerm ||
                    prop.name.toLowerCase().includes(searchTerm) ||
                    prop.title.toLowerCase().includes(searchTerm) ||
                    prop.description.toLowerCase().includes(searchTerm);

                const matchesSemantic = !semanticType || prop.semanticType === semanticType;
                const matchesIndustry = !industry || prop.industry === industry;
                const matchesUnit = !unit || prop.unit === unit;

                return matchesSearch && matchesSemantic && matchesIndustry && matchesUnit;
            });

            renderProperties();
            updateResultsInfo();
        }

        function updateResultsInfo() {
            const info = document.getElementById('resultsInfo');
            const total = properties.length;
            const filtered = filteredProperties.length;

            if (filtered === total) {
                info.textContent = `Showing all ${total} properties`;
            } else {
                info.textContent = `Showing ${filtered} of ${total} properties`;
            }
        }

        // Event listeners
        document.getElementById('searchInput').addEventListener('input', applyFilters);
        document.getElementById('semanticFilter').addEventListener('change', applyFilters);
        document.getElementById('industryFilter').addEventListener('change', applyFilters);
        document.getElementById('unitFilter').addEventListener('change', applyFilters);

        // Initialize
        fetchThingDescription();
    </script>
</body>
</html>
    """
    return web.Response(text=html, content_type="text/html")
