#!/usr/bin/env python3
"""
Generate departmental budget reports with HTML tables and charts for Squarespace.
Creates individual department reports similar to the AGR example provided.
"""

import pandas as pd
# Disable pandas' IPython display integration
pd.set_option('display.notebook_repr_html', False)
pd.set_option('display.max_columns', None)

import matplotlib
# Set the backend to 'Agg' to prevent display issues
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path
import base64
import json  # For embedding chart data as JSON
import io
from io import BytesIO
import argparse
import logging
import traceback
import sys

# Ensure matplotlib doesn't try to use display
os.environ['MPLBACKEND'] = 'Agg'
plt.ioff()  # Turn off interactive mode

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default department description to use when none is found
DEFAULT_DEPT_DESCRIPTION = "No description available for this department."

class DepartmentalBudgetAnalyzer:
    """Generate departmental budget reports with HTML tables and charts."""
    
    def __init__(self, data_file: str, output_dir: str = "data/output/departmental_reports",
                 descriptions_file: str = "data/processed/department_descriptions.json"):
        """
        Initialize the analyzer.
        
        Args:
            data_file: Path to the budget allocations CSV file
            output_dir: Directory to save HTML reports
            descriptions_file: Path to the JSON file containing department descriptions
        """
        self.data_file = data_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load data
        self.df = pd.read_csv(data_file)
        logger.info(f"Loaded {len(self.df)} budget allocations")
        
        # Load department descriptions
        self.descriptions = self._load_descriptions(descriptions_file)
        
        # Fund type mappings to match the reference
        self.fund_mappings = {
            'A': 'General Funds',
            'B': 'Special Funds', 
            'N': 'Federal Funds',
            'P': 'Federal Funds',  # Other Federal Funds -> Federal Funds
            'W': 'Other Funds',    # Revolving Funds -> Other Funds
            'T': 'Other Funds',    # Trust Funds -> Other Funds
            'U': 'Other Funds',    # Interdepartmental Transfers -> Other Funds
            'R': 'Other Funds',    # Reimbursements -> Other Funds
            'S': 'Other Funds'     # Other Special Funds -> Other Funds
        }
        
        # Colors for charts (matching official style)
        self.colors = {
            'General Funds': '#1f77b4',      # Blue
            'Special Funds': '#2ca02c',      # Green  
            'Federal Funds': '#2c3e50',      # Dark blue/gray
            'Other Funds': '#17a2b8'         # Cyan
        }
        
        # Department code to full name mapping
        self.department_names = {
            'AGR': 'AGRICULTURE',
            'AGS': 'ACCOUNTING AND GENERAL SERVICES',
            'ATG': 'ATTORNEY GENERAL',
            'BED': 'BUSINESS, ECONOMIC DEVELOPMENT & TOURISM',
            'BUF': 'BUDGET AND FINANCE',
            'CCA': 'COMMERCE AND CONSUMER AFFAIRS',
            'CCH': 'CITY AND COUNTY OF HONOLULU',
            'COH': 'COUNTY OF HAWAII',
            'COK': 'COUNTY OF KAUAI',
            'DEF': 'DEFENSE',
            'EDN': 'EDUCATION',
            'GOV': 'GOVERNOR',
            'HHL': 'HAWAIIAN HOME LANDS',
            'HMS': 'HUMAN SERVICES',
            'HRD': 'HUMAN RESOURCES DEVELOPMENT',
            'HTH': 'HEALTH',
            'LAW': 'LAW ENFORCEMENT',
            'LBR': 'LABOR AND INDUSTRIAL RELATIONS',
            'LNR': 'LAND AND NATURAL RESOURCES',
            'LTG': 'LIEUTENANT GOVERNOR',
            'P': 'LEGISLATURE',
            'PSD': 'PUBLIC SAFETY',
            'TAX': 'TAXATION',
            'TRN': 'TRANSPORTATION',
            'UOH': 'UNIVERSITY OF HAWAII'
        }
        
        # Department code to display name mapping (for the descriptions)
        self.display_names = {
            'AGR': 'Department of Agriculture',
            'AGS': 'Department of Accounting & General Services',
            'ATG': 'Department of the Attorney General',
            'BED': 'Department of Business, Economic Development & Tourism',
            'BUF': 'Department of Budget & Finance',
            'CCA': 'Department of Commerce & Consumer Affairs',
            'CCH': 'City and County of Honolulu',
            'COH': 'County of Hawaii',
            'COK': 'County of Kauai',
            'DEF': 'Department of Defense',
            'EDN': 'Department of Education',
            'GOV': 'Office of the Governor',
            'HHL': 'Department of Hawaiian Home Lands',
            'HMS': 'Department of Human Services',
            'HRD': 'Department of Human Resources Development',
            'HTH': 'Department of Health',
            'LAW': 'Department of Law Enforcement',
            'LBR': 'Department of Labor & Industrial Relations',
            'LNR': 'Department of Land & Natural Resources',
            'LTG': 'Office of the Lieutenant Governor',
            'P': 'State Legislature',
            'PSD': 'Department of Corrections and Rehabilitation',
            'TAX': 'Department of Taxation',
            'TRN': 'Department of Transportation',
            'UOH': 'University of Hawaii System'
        }
    
    def get_department_summary(self, dept_code: str) -> dict:
        """
        Get comprehensive budget summary for a department.
        
        Args:
            dept_code: Department code (e.g., 'AGR')
            
        Returns:
            Dictionary with department budget breakdown
        """
        dept_data = self.df[self.df['department_code'] == dept_code].copy()
        
        if dept_data.empty:
            logger.warning(f"No data found for department {dept_code}")
            return None
        
        # Use full department name from mapping
        dept_name = self.department_names.get(dept_code, dept_code)
        
        # Map fund types
        dept_data['fund_category_mapped'] = dept_data['fund_type'].map(self.fund_mappings)
        
        # Calculate operating budget by fund type
        operating_data = dept_data[dept_data['section'] == 'Operating']
        operating_by_fund = operating_data.groupby('fund_category_mapped')['amount'].sum()
        
        # Calculate CIP projects (Capital Improvement section)
        cip_data = dept_data[dept_data['section'] == 'Capital Improvement']
        cip_total = cip_data['amount'].sum()
        
        # Calculate other appropriations (non-operating, non-CIP)
        other_data = dept_data[(dept_data['section'] != 'Operating') & (dept_data['section'] != 'Capital Improvement')]
        other_total = other_data['amount'].sum()
        
        # Total operating budget (excluding one-time appropriations)
        total_operating = operating_by_fund.sum()
        
        # Handle one-time appropriations separately
        one_time_data = dept_data[dept_data['section'] == 'One-Time']
        one_time_by_fund = pd.Series(dtype=float)
        one_time_total = 0
        
        if not one_time_data.empty:
            one_time_by_fund = one_time_data.groupby('fund_category_mapped')['amount'].sum()
            one_time_total = one_time_by_fund.sum()
        
        # Overall total includes operating + one-time + other appropriations
        total_budget = total_operating + one_time_total + other_total
        
        summary = {
            'department_code': dept_code,
            'department_name': dept_name,
            'total_budget': total_budget,
            'operating_budget': {
                'General Funds': operating_by_fund.get('General Funds', 0),
                'Special Funds': operating_by_fund.get('Special Funds', 0),
                'Federal Funds': operating_by_fund.get('Federal Funds', 0),
                'Other Funds': operating_by_fund.get('Other Funds', 0),
                'total': total_operating
            },
            'one_time_appropriations': {
                'General Funds': one_time_by_fund.get('General Funds', 0),
                'Special Funds': one_time_by_fund.get('Special Funds', 0),
                'Federal Funds': one_time_by_fund.get('Federal Funds', 0),
                'Other Funds': one_time_by_fund.get('Other Funds', 0),
                'total': one_time_total
            },
            'other_appropriations': other_total,
            'cip_projects': cip_total,
            'raw_data': dept_data
        }
        
        return summary
    
    def create_department_chart(self, summary: dict) -> str:
        """
        Create a horizontal stacked bar chart for department budget with non-overlapping labels.
        
        Args:
            summary: Department summary dictionary
            
        Returns:
            Base64 encoded image string
        """
        try:
            plt.switch_backend('Agg')
            plt.rcParams.update({'font.size': 14, 'axes.titlesize': 16, 'axes.labelsize': 14})
            
            fig, ax = plt.subplots(figsize=(16, 8), dpi=150)
            
            fund_types = ['General Funds', 'Special Funds', 'Federal Funds', 'Other Funds']
            amounts = [summary['operating_budget'][ft] / 1_000_000 for ft in fund_types]
            colors = [self.colors[ft] for ft in fund_types]
            
            filtered_data = sorted([(amt, color, label) for amt, color, label in 
                                  zip(amounts, colors, fund_types) if amt > 0],
                                 key=lambda x: x[0], reverse=True)
            
            if not filtered_data:
                ax.text(0.5, 0.5, 'No Operating Budget Data', 
                        ha='center', va='center', fontsize=16)
                ax.axis('off')
            else:
                amounts, colors, fund_types = zip(*filtered_data)
                total_amount = sum(amounts)
                left = 0
                
                bars = ax.barh(0, amounts[0], left=left, color=colors[0], 
                              label=fund_types[0], height=0.6, alpha=0.9)
                bars_list = [bars[0]]
                label_positions = []
                text_objects = []
                
                for i, (amount, color, label) in enumerate(zip(amounts, colors, fund_types)):
                    segment_center = left + amount/2
                    # Format as billions if ≥ 1000 million, otherwise as millions
                    if amount >= 1000:
                        text = f'${amount/1000:,.1f}B'
                    else:
                        text = f'${amount:,.0f}M'
                    
                    if amount > total_amount * 0.1:  
                        brightness = sum(matplotlib.colors.to_rgb(color)[:3])/3
                        text_color = 'white' if brightness < 0.6 else 'black'
                        
                        txt = ax.text(segment_center, 0, text, 
                                     ha='center', va='center',
                                     color=text_color,
                                     fontweight='bold', 
                                     fontsize=14,
                                     bbox=dict(facecolor='none', 
                                               edgecolor='none',
                                               alpha=0.7,
                                               boxstyle='round,pad=0.2'))
                        label_positions.append((left, left + amount))
                        text_objects.append(txt)
                    else:
                        label_positions.append(None)
                        text_objects.append(None)
                    
                    if i < len(amounts) - 1:
                        left += amount
                        bar = ax.barh(0, amounts[i+1], left=left, 
                                    color=colors[i+1], 
                                    label=fund_types[i+1], 
                                    height=0.6, 
                                    alpha=0.9)
                        bars_list.append(bar[0])
                
                for i, (amount, color, label) in enumerate(zip(amounts, colors, fund_types)):
                    if label_positions[i] is None or amount <= total_amount * 0.1:
                        segment_start = sum(amounts[:i])
                        segment_end = segment_start + amount
                        
                        if text_objects[i] is not None:
                            text_objects[i].remove()
                        
                        y_offset = 0
                        for offset in [0.7, -0.7, 1.4, -1.4, 2.1, -2.1]:
                            overlap = False
                            for j, pos in enumerate(label_positions):
                                if pos is None or j == i:
                                    continue
                                start, end = pos
                                if ((segment_start <= end and segment_end >= start) or
                                    (segment_start >= start and segment_start <= end) or
                                    (segment_end >= start and segment_end <= end)):
                                    overlap = True
                                    break
                            if not overlap:
                                y_offset = offset
                                break
                        
                        # Format as billions if ≥ 1000 million, otherwise as millions
                        if amount >= 1000:
                            amount_text = f'${amount/1000:,.1f}B'
                        else:
                            amount_text = f'${amount:,.0f}M'
                        
                        txt = ax.text(segment_start + amount/2, y_offset, amount_text,
                                     ha='center', va='center',
                                     bbox=dict(facecolor='white', 
                                               alpha=0.9, 
                                               edgecolor='#666666',
                                               boxstyle='round,pad=0.6'),
                                     fontsize=12,
                                     fontweight='bold')
                        
                        if y_offset != 0:
                            ax.plot([segment_start + amount/2, segment_start + amount/2], 
                                    [0 if y_offset > 0 else -0.3, y_offset * 0.9], 
                                    'k-', lw=1.5, alpha=0.6)
                
                ax.set_xlim(0, total_amount * 1.2)  
                ax.set_ylim(-3, 3)  
                
                ax.xaxis.grid(True, linestyle='--', alpha=0.3, color='#666666')
                ax.set_xlabel('Amount (Millions of Dollars)', 
                            fontsize=14, 
                            labelpad=15,
                            fontweight='bold')
                ax.set_yticks([])  
                
                for spine in ax.spines.values():
                    spine.set_visible(False)
                
                if len(fund_types) > 1:
                    # Create legend with proper formatting
                    legend = ax.legend(
                        handles=bars_list,
                        labels=fund_types,  # Explicitly set labels from fund_types
                        bbox_to_anchor=(0.5, -0.15), 
                        loc='upper center',
                        ncol=min(4, len(fund_types)),  # Limit columns for better layout
                        frameon=False,
                        fontsize=12,
                        handletextpad=0.8,
                        columnspacing=1.5,
                        borderpad=1.0
                    )
                    
                    # Make legend text bold and set proper color
                    for text in legend.get_texts():
                        text.set_fontweight('bold')
                        text.set_color('#2c3e50')  # Dark gray for better readability

            plt.tight_layout(pad=3.0)
            
            # Set title with improved styling
            ax.set_title(
                f'{summary["department_code"]} Operating Budget (FY26)',
                fontsize=24,
                pad=20,
                fontweight='bold',
                color='#2c3e50'
            )
            
            # Save to bytes buffer with high quality settings
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            # Encode to base64
            data = base64.b64encode(buf.getbuffer()).decode('ascii')
            return data
            
        except Exception as e:
            logger.error(f"Error creating chart for {summary.get('department_code', 'unknown')}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return a simple placeholder image as base64
            try:
                fig, ax = plt.subplots(figsize=(10, 2))
                ax.text(0.5, 0.5, f'Chart Error: {str(e)[:50]}...', 
                       ha='center', va='center', fontsize=10)
                ax.axis('off')
                
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.getvalue()).decode()
                plt.close(fig)
                plt.clf()
                
                return image_base64
            except:
                return ""
    
    def _load_descriptions(self, descriptions_file: str) -> dict:
        """
        Load department descriptions from a JSON file.
        
        Args:
            descriptions_file: Path to the JSON file containing department descriptions
            
        Returns:
            Dictionary mapping department codes to their descriptions
        """
        try:
            with open(descriptions_file, 'r', encoding='utf-8') as f:
                descriptions = json.load(f)
            logger.info(f"Loaded descriptions for {len(descriptions)} departments")
            return descriptions
        except FileNotFoundError:
            logger.warning(f"Department descriptions file not found: {descriptions_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing department descriptions: {e}")
            return {}
    
    def get_department_description(self, dept_code: str) -> str:
        """
        Get the description for a department.
        
        Args:
            dept_code: Department code (e.g., 'AGR')
            
        Returns:
            Department description as a string
        """
        # Get the display name for the department
        display_name = self.display_names.get(dept_code, dept_code)
        
        # Try to get the description for the department
        dept_info = self.descriptions.get(dept_code, {})
        
        # If we have a description, use it
        if 'description' in dept_info:
            return dept_info['description']
            
        # Otherwise, use the display name with a default message
        return f"{display_name} is a department of the State of Hawaii. {DEFAULT_DEPT_DESCRIPTION}"
    
    def _get_css_styles(self) -> str:
        """Return the CSS styles for the HTML report."""
        return """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }
        
        .header h1 {
            color: #2c3e50;
            margin: 0;
            font-size: 2.2em;
        }
        
        .header h2 {
            color: #7f8c8d;
            margin: 10px 0 0 0;
            font-weight: normal;
        }
        
        .budget-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        
        .budget-table th {
            background-color: #3498db;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: bold;
        }
        
        .budget-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }
        
        .budget-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .budget-table tr:hover {
            background-color: #e8f4fd;
        }
        
        .amount {
            text-align: right;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .total-row {
            background-color: #3498db !important;
            color: white;
            font-weight: bold;
        }
        
        .total-row td {
            border-bottom: none;
        }
        
        .chart-container {
            text-align: center;
            margin: 20px auto;
            padding: 20px;
            background-color: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid rgba(0,0,0,0.05);
            max-width: 1200px;
            width: 95%;
            box-sizing: border-box;
            overflow: hidden;
        }
        
        .chart-container h3 {
            color: #2c3e50;
            margin: 0 0 15px 0;
            padding: 0;
            font-size: 1.5em;
            font-weight: 600;
        }
        
        .chart-container .chart-wrapper {
            width: 100%;
            margin: 0 auto;
            overflow: visible;
            text-align: center;
        }
        
        .chart-container img {
            max-width: 100%;
            height: auto;
            max-height: 600px;
            width: auto;
            border-radius: 8px;
            margin: 0 auto;
            display: block;
            object-fit: contain;
        }
        
        @media (max-width: 1200px) {
            .chart-container {
                padding: 15px;
                width: 98%;
            }
            
            .chart-container img {
                max-height: 500px;
            }
        }
        
        @media (max-width: 768px) {
            .chart-container {
                padding: 10px;
                margin: 10px auto;
            }
            
            .chart-container img {
                max-height: 400px;
            }
        }
        
        .summary-stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 30px 0;
        }
        
        .budget-card {
            background-color: #fff;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            text-align: center;
            flex: 0 1 300px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .budget-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }
        
        .budget-amount {
            font-size: 2.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
        }
        
        .budget-label {
            color: #7f8c8d;
            font-size: 1.1em;
            font-weight: 500;
        }
        
        .footer {
            margin-top: 40px;
            padding: 20px;
            background-color: #ecf0f1;
            border-radius: 8px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .dept-description {
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }
        
        .dept-description h3 {
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 1.4em;
        }
        
        .dept-description p {
            margin: 0;
            line-height: 1.6;
            color: #4a5568;
        }
        """
    
    def _format_currency(self, amount: float) -> str:
        """Format currency amounts for display with up to 2 decimal places."""
        if amount >= 1_000_000_000:
            value = amount / 1_000_000_000
            if value == int(value):
                return f"${value:,.0f}B"
            elif value * 10 == int(value * 10):
                return f"${value:,.1f}B"
            else:
                return f"${value:,.2f}B"
        else:
            value = amount / 1_000_000
            if value == int(value):
                return f"${value:,.0f}M"
            elif value * 10 == int(value * 10):
                return f"${value:,.1f}M"
            else:
                return f"${value:,.2f}M"
    
    def _format_currency_long(self, amount: float) -> str:
        """Format currency amounts for display with long form and up to 2 decimal places."""
        if amount >= 1_000_000_000:
            value = amount / 1_000_000_000
            if value == int(value):
                return f"${value:,.0f} Billion"
            elif value * 10 == int(value * 10):
                return f"${value:,.1f} Billion"
            else:
                return f"${value:,.2f} Billion"
        else:
            value = amount / 1_000_000
            if value == int(value):
                return f"${value:,.0f} Million"
            elif value * 10 == int(value * 10):
                return f"${value:,.1f} Million"
            else:
                return f"${value:,.2f} Million"
    
    def _build_summary_cards(self, summary: dict) -> str:
        """Build the summary cards section."""
        operating_total = summary['operating_budget']['total']
        one_time_total = summary['one_time_appropriations']['total']
        cip_total = summary['cip_projects']
        
        # Build cards - always show operating and CIP, conditionally show one-time
        cards_html = f"""
        <div class="budget-card">
            <div class="budget-amount">{self._format_currency(operating_total)}</div>
            <div class="budget-label">Operating Budget</div>
        </div>"""
        
        # Add one-time appropriations card if there are any
        if one_time_total > 0:
            cards_html += f"""
        <div class="budget-card">
            <div class="budget-amount">{self._format_currency(one_time_total)}</div>
            <div class="budget-label">One-Time Appropriations</div>
        </div>"""
        
        cards_html += f"""
        <div class="budget-card">
            <div class="budget-amount">{self._format_currency(cip_total)}</div>
            <div class="budget-label">Capital Improvement Projects</div>
        </div>"""
        
        return f"""
    <div class="summary-stats">
        {cards_html}
    </div>"""
    
    def _build_budget_table(self, summary: dict) -> str:
        """Build the budget breakdown table."""
        op_budget = summary['operating_budget']
        one_time_budget = summary['one_time_appropriations']
        dept_code = summary['department_code']
        
        # Build operating budget section
        table_html = f"""
    <table class="budget-table">
        <thead>
            <tr>
                <th>{dept_code} FY26 Operating Budget:</th>
                <th class="amount">{self._format_currency_long(op_budget['total'])}</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>General Funds:</td>
                <td class="amount">{self._format_currency(op_budget['General Funds'])}</td>
            </tr>
            <tr>
                <td>Special Funds:</td>
                <td class="amount">{self._format_currency(op_budget['Special Funds'])}</td>
            </tr>
            <tr>
                <td>Federal Funds:</td>
                <td class="amount">{self._format_currency(op_budget['Federal Funds'])}</td>
            </tr>
            <tr>
                <td>Other Funds:</td>
                <td class="amount">{self._format_currency(op_budget['Other Funds'])}</td>
            </tr>"""
        
        # Add one-time appropriations section if there are any
        if one_time_budget['total'] > 0:
            table_html += f"""
            <tr class="total-row">
                <td>FY26 One-Time Appropriations:</td>
                <td class="amount">{self._format_currency_long(one_time_budget['total'])}</td>
            </tr>
            <tr>
                <td>General Funds:</td>
                <td class="amount">{self._format_currency(one_time_budget['General Funds'])}</td>
            </tr>
            <tr>
                <td>Special Funds:</td>
                <td class="amount">{self._format_currency(one_time_budget['Special Funds'])}</td>
            </tr>
            <tr>
                <td>Federal Funds:</td>
                <td class="amount">{self._format_currency(one_time_budget['Federal Funds'])}</td>
            </tr>
            <tr>
                <td>Other Funds:</td>
                <td class="amount">{self._format_currency(one_time_budget['Other Funds'])}</td>
            </tr>"""
        
        # Add CIP section
        table_html += f"""
            <tr class="total-row">
                <td>FY26 Capital Improvement Projects:</td>
                <td class="amount">{self._format_currency_long(summary['cip_projects'])}</td>
            </tr>
        </tbody>
    </table>"""
        
        return table_html
    
    def _build_chart_section(self, summary: dict, chart_base64: str) -> str:
        """Build the chart section."""
        dept_code = summary['department_code']
        
        return f"""
    <div class="chart-container">
        <h3>Figure 15. {dept_code} Operating Budget</h3>
        <div class="chart-wrapper">
            <img src="data:image/png;base64,{chart_base64}" alt="{dept_code} Budget Chart">
        </div>
    </div>"""
    
    def generate_html_report(self, summary: dict) -> str:
        """
        Generate HTML report for a department using template-based approach.
        
        Args:
            summary: Department summary dictionary
            
        Returns:
            HTML string
        """
        # Generate chart
        chart_base64 = self.create_department_chart(summary)
        
        # Get department info
        dept_code = summary['department_code']
        dept_name = summary['department_name']
        dept_description = self.get_department_description(dept_code)
        
        # Build template sections
        css_styles = self._get_css_styles()
        summary_cards = self._build_summary_cards(summary)
        budget_table = self._build_budget_table(summary)
        chart_section = self._build_chart_section(summary, chart_base64)
        
        # Assemble the complete HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dept_code} FY26 Budget Report</title>
    <style>{css_styles}</style>
</head>
<body>
    <div class="header">
        <h1>{dept_code} FY26 Operating Budget</h1>
        <h2>{dept_name}</h2>
    </div>
    
    <div class="dept-description">
        <h3>About {dept_name}</h3>
        <p>{dept_description}</p>
    </div>
    
    {summary_cards}
    
    {budget_table}
    
    {chart_section}
    
    <div class="footer">
        <p>Generated from Hawaii State Budget FY 2026 Post-Veto Data</p>
        <p>Data source: HB300 CD1 - State of Hawaii Operating and Capital Budget</p>
    </div>
</body>
</html>
"""
        return html_content
    
    def generate_all_reports(self):
        """Generate HTML reports for all departments."""
        # Get all unique department codes
        dept_codes = sorted(self.df['department_code'].unique())
        
        logger.info(f"Generating reports for {len(dept_codes)} departments")
        
        # Create index page
        index_html = self.create_index_page(dept_codes)
        index_path = self.output_dir / "index.html"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
        logger.info(f"Created index page: {index_path}")
        
        # Generate individual department reports
        for dept_code in dept_codes:
            try:
                logger.info(f"Processing department: {dept_code}")
                summary = self.get_department_summary(dept_code)
                if summary:
                    logger.info(f"Got summary for {dept_code}, generating HTML report...")
                    html_report = self.generate_html_report(summary)
                    
                    # Save to file
                    filename = f"{dept_code.lower()}_budget_report.html"
                    filepath = self.output_dir / filename
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_report)
                    
                    logger.info(f"Successfully generated report for {dept_code}: {filepath}")
                else:
                    logger.warning(f"Skipped {dept_code} - no data available")
                    
            except Exception as e:
                logger.error(f"Error generating report for {dept_code}: {e}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # Continue with next department instead of stopping
    
    def create_index_page(self, dept_codes: list) -> str:
        """Create an index page linking to all department reports."""
        # Get department names and budget breakdown
        dept_info = []
        for code in dept_codes:
            dept_data = self.df[self.df['department_code'] == code]
            if not dept_data.empty:
                # Use full department name from mapping
                name = self.department_names.get(code, code)
                total = dept_data['amount'].sum() / 1_000_000
                
                # Calculate operating vs capital vs one-time breakdown
                operating = dept_data[dept_data['section'] == 'Operating']['amount'].sum() / 1_000_000
                capital = dept_data[dept_data['section'] == 'Capital Improvement']['amount'].sum() / 1_000_000
                one_time = dept_data[dept_data['section'] == 'One-Time']['amount'].sum() / 1_000_000
                
                dept_info.append((code, name, total, operating, capital, one_time))
        
        # Sort by operating budget (descending), then by total budget (descending)
        dept_info.sort(key=lambda x: (-x[3], -x[2]))  # x[3] is operating budget, x[2] is total budget
        
        # Calculate totals for summary cards
        total_budget = sum(info[2] for info in dept_info)
        total_departments = len(dept_info)
        largest_dept = dept_info[0] if dept_info else ('', '', 0)
        
        # Calculate operating vs capital vs one-time budget totals
        operating_total = self.df[self.df['section'] == 'Operating']['amount'].sum() / 1_000_000
        capital_total = self.df[self.df['section'] == 'Capital Improvement']['amount'].sum() / 1_000_000
        one_time_total = self.df[self.df['section'] == 'One-Time']['amount'].sum() / 1_000_000
        
        # Helper function to format budget amounts with up to 2 decimal places
        def format_budget(amount_millions):
            if amount_millions >= 1000:
                value = amount_millions / 1000
                if value == int(value):
                    return f"${value:,.0f}B"
                elif value * 10 == int(value * 10):
                    return f"${value:,.1f}B"
                else:
                    return f"${value:,.2f}B"
            else:
                if amount_millions == int(amount_millions):
                    return f"${amount_millions:,.0f}M"
                elif amount_millions * 10 == int(amount_millions * 10):
                    return f"${amount_millions:,.1f}M"
                else:
                    return f"${amount_millions:,.2f}M"
        
        # Prepare chart data JSON for embedding in the JavaScript code
        chart_data = [
            {
                "code": code,
                "name": name,
                "operating": operating,
                "capital": capital,
                "one_time": one_time
            } for code, name, total, operating, capital, one_time in dept_info
        ]
        chart_data_json = json.dumps(chart_data)
        print(f"DEBUG: chart_data_json = {chart_data_json}")
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hawaii State Budget FY 2026 - Departmental Reports</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #1a202c;
            background: linear-gradient(135deg, #007fb2 0%, #005a7d 100%);
            min-height: 100vh;
            font-size: 16px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 40px;
            background-color: #fff;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            color: #1a202c;
            margin: 0 0 12px 0;
            font-size: 3rem;
            font-weight: 700;
            letter-spacing: -0.025em;
        }}
        
        .header p {{
            color: #4a5568;
            font-size: 1.25rem;
            font-weight: 400;
            margin: 0;
        }}
        
        .summary-section {{
            margin-bottom: 40px;
        }}
        
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 4px 20px rgba(0,127,178,0.1);
            border: 1px solid rgba(0,127,178,0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }}
        
        .summary-card h3 {{
            font-size: 0.875rem;
            font-weight: 600;
            color: #4a5568;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}
        
        .summary-card .value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #1a202c;
            line-height: 1;
            margin-bottom: 4px;
        }}
        
        .summary-card .label {{
            font-size: 1rem;
            color: #718096;
            font-weight: 500;
        }}
        
        .search-section {{
            background-color: #fff;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 32px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        
        .search-container {{
            position: relative;
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .search-row {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        
        .search-input-container {{
            position: relative;
            width: 100%;
        }}
        
        .sort-buttons {{
            display: flex;
            gap: 12px;
            justify-content: flex-start;
            flex-wrap: wrap;
        }}
        
        .sort-btn {{
            display: flex;
            align-items: center;
            gap: 6px;
            background-color: #f1f5f9;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px 16px;
            font-size: 0.9rem;
            font-weight: 600;
            color: #475569;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .sort-btn:hover {{
            background-color: #e2e8f0;
            border-color: #cbd5e1;
        }}
        
        .sort-btn.active {{
            background-color: #007fb2;
            border-color: #007fb2;
            color: white;
        }}
        
        .sort-arrow {{
            font-size: 0.8rem;
            transition: transform 0.2s ease;
        }}
        
        .sort-btn[data-order="asc"] .sort-arrow {{
            transform: rotate(180deg);
        }}
        
        .search-input {{
            width: 100%;
            padding: 16px 24px 16px 48px;
            font-size: 1.125rem;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            background-color: #f8fafc;
            transition: all 0.2s ease;
            font-family: inherit;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: #007fb2;
            background-color: #fff;
            box-shadow: 0 0 0 3px rgba(0, 127, 178, 0.1);
        }}
        
        .search-icon {{
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            color: #a0aec0;
            font-size: 1.25rem;
        }}
        
        .departments-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 24px;
            margin: 32px 0;
        }}
        
        .dept-card {{
            background: linear-gradient(135deg, #f8fcff 0%, #eef7ff 100%);
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 4px 20px rgba(0,127,178,0.08);
            transition: all 0.3s ease;
            text-decoration: none;
            color: inherit;
            border: 1px solid rgba(0,127,178,0.15);
            position: relative;
            overflow: hidden;
        }}
        
        .dept-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #007fb2 0%, #005a7d 100%);
        }}
        
        .dept-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            text-decoration: none;
            color: inherit;
        }}
        
        .dept-name {{
            font-size: 1.375rem;
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 12px;
            line-height: 1.3;
            letter-spacing: -0.025em;
        }}
        
        .dept-code {{
            font-size: 0.75rem;
            font-weight: 600;
            color: #007fb2;
            background: linear-gradient(135deg, #e6f3ff 0%, #d9ecff 100%);
            padding: 6px 12px;
            border-radius: 8px;
            display: inline-block;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .dept-budget {{
            color: #38a169;
            font-weight: 700;
            font-size: 1.5rem;
            letter-spacing: -0.025em;
            margin-bottom: 16px;
        }}
        
        .dept-breakdown {{
            display: flex;
            gap: 16px;
            margin-top: 8px;
        }}
        
        .breakdown-item {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            flex: 1;
        }}
        
        .breakdown-label {{
            font-size: 0.75rem;
            font-weight: 500;
            color: #718096;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}
        
        .breakdown-value {{
            font-size: 1rem;
            font-weight: 600;
            color: #2d3748;
        }}
        
        .chart-section {{
            margin-bottom: 40px;
        }}
        
        .chart-container {{
            background-color: #fff;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 4px 20px rgba(0,127,178,0.08);
            border: 1px solid rgba(0,127,178,0.1);
        }}
        
        .chart-title {{
            font-size: 1.75rem;
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 32px;
            text-align: center;
        }}
        
        .chart-wrapper {{
            display: flex;
            flex-direction: column;
            gap: 16px;
            max-height: 600px;
            overflow-y: auto;
        }}
        
        .dept-chart-row {{
            display: flex;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .dept-chart-row:last-child {{
            border-bottom: none;
        }}
        
        .dept-label {{
            width: 200px;
            font-size: 0.875rem;
            font-weight: 600;
            color: #007fb2;
            text-decoration: none;
            flex-shrink: 0;
            cursor: pointer;
            transition: color 0.2s ease;
        }}
        
        .dept-label:hover {{
            color: #005a7d;
            text-decoration: underline;
        }}
        
        .chart-bars {{
            display: flex;
            flex: 1;
            gap: 8px;
            align-items: center;
            margin-left: 16px;
        }}
        
        .bar-group {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            flex: 1;
        }}
        
        .bar-container {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .bar-label {{
            font-size: 0.75rem;
            font-weight: 500;
            color: #4a5568;
            width: 60px;
            text-align: right;
        }}
        
        .bar {{
            height: 20px;
            border-radius: 4px;
            position: relative;
            min-width: 2px;
            transition: all 0.3s ease;
        }}
        
        .bar-operating {{
            background: linear-gradient(90deg, #007fb2 0%, #0099d4 100%);
        }}
        
        .bar-capital {{
            background: linear-gradient(90deg, #38a169 0%, #48bb78 100%);
        }}
        
        .bar-value {{
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }}
        
        .chart-legend {{
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid #e2e8f0;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }}
        
        .legend-operating {{
            background: linear-gradient(90deg, #007fb2 0%, #0099d4 100%);
        }}
        
        .legend-capital {{
            background: linear-gradient(90deg, #38a169 0%, #48bb78 100%);
        }}
        
        .legend-text {{
            font-size: 0.875rem;
            font-weight: 500;
            color: #4a5568;
        }}
        
        .footer {{
            margin-top: 60px;
            padding: 32px;
            background-color: #fff;
            border-radius: 16px;
            text-align: center;
            color: #4a5568;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        
        .footer p {{
            font-size: 0.875rem;
            font-weight: 500;
        }}
        
        .hidden {{
            display: none !important;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2.25rem;
            }}
            
            .summary-cards {{
                grid-template-columns: 1fr;
            }}
            
            .departments-grid {{
                grid-template-columns: 1fr;
            }}
            
            .dept-card {{
                padding: 24px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Hawaii State Budget FY 2026</h1>
        <p>Departmental Budget Reports (Post-Veto)</p>
    </div>
    
    <div class="summary-section">
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Total Budget</h3>
                <div class="value">{format_budget(total_budget)}</div>
                <div class="label">All Departments</div>
            </div>
            <div class="summary-card">
                <h3>Departments</h3>
                <div class="value">{total_departments}</div>
                <div class="label">State Agencies</div>
            </div>
            <div class="summary-card">
                <h3>Largest Department</h3>
                <div class="value">{format_budget(largest_dept[2])}</div>
                <div class="label">{largest_dept[1]}</div>
            </div>
        </div>
        
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Operating Budget</h3>
                <div class="value">{format_budget(operating_total)}</div>
                <div class="label">All Departments Combined</div>
            </div>
            <div class="summary-card">
                <h3>One-Time Appropriations</h3>
                <div class="value">{format_budget(one_time_total)}</div>
                <div class="label">Special Allocations</div>
            </div>
            <div class="summary-card">
                <h3>Capital Budget</h3>
                <div class="value">{format_budget(capital_total)}</div>
                <div class="label">Capital Improvement Projects</div>
            </div>
        </div>
    </div>
    

    <div class="search-section">
        <div class="search-container">
            <div class="search-row">
                <div class="search-input-container">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="searchInput" class="search-input" placeholder="Search departments by name or code...">
                </div>
                <div class="sort-buttons">
                    <button class="sort-btn" data-sort="operating" data-order="desc">
                        <span>Operating Budget</span>
                        <span class="sort-arrow">↓</span>
                    </button>
                    <button class="sort-btn" data-sort="capital" data-order="desc">
                        <span>Capital Budget</span>
                        <span class="sort-arrow">↓</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <div class="departments-grid" id="departmentsGrid">
"""
        
        for code, name, total, operating, capital, one_time in dept_info:
            # Format the budget amounts with up to 2 decimal places
            def format_amount(amount):
                if amount >= 1000:
                    value = amount / 1000
                    if value == int(value):
                        return f"${value:,.0f}B"
                    elif value * 10 == int(value * 10):
                        return f"${value:,.1f}B"
                    else:
                        return f"${value:,.2f}B"
                else:
                    if amount == int(amount):
                        return f"${amount:,.0f}M"
                    elif amount * 10 == int(amount * 10):
                        return f"${amount:,.1f}M"
                    else:
                        return f"${amount:,.2f}M"
            
            total_display = format_amount(total)
            operating_display = format_amount(operating)
            capital_display = format_amount(capital)
            one_time_display = format_amount(one_time)
            
            # Build breakdown items - always show operating and capital, conditionally show one-time
            breakdown_items = f"""
                <div class="breakdown-item">
                    <span class="breakdown-label">Operating:</span>
                    <span class="breakdown-value">{operating_display}</span>
                </div>"""
            
            if one_time > 0:
                breakdown_items += f"""
                <div class="breakdown-item">
                    <span class="breakdown-label">One-Time:</span>
                    <span class="breakdown-value">{one_time_display}</span>
                </div>"""
            
            breakdown_items += f"""
                <div class="breakdown-item">
                    <span class="breakdown-label">Capital:</span>
                    <span class="breakdown-value">{capital_display}</span>
                </div>"""
            
            html += f"""
        <a href="{code.lower()}_budget_report.html" class="dept-card" data-operating="{operating}" data-capital="{capital}" data-onetime="{one_time}">
            <div class="dept-name">{name}</div>
            <div class="dept-code">{code}</div>
            <div class="dept-budget">{total_display} Total Budget</div>
            <div class="dept-breakdown">
                {breakdown_items}
            </div>
        </a>
"""
        
        html += """
    </div>
    
    <div class="footer">
        <p>Generated from Hawaii State Budget FY 2026 Post-Veto Data</p>
        <p>Data source: HB300 CD1 - State of Hawaii Operating and Capital Budget</p>
    </div>
    
    <script>
        // Search functionality
        document.addEventListener('DOMContentLoaded', function() {
            const searchInput = document.getElementById('searchInput');
            const departmentsGrid = document.getElementById('departmentsGrid');
            
            // Create no results message element
            const noResultsMsg = document.createElement('div');
            noResultsMsg.id = 'noResultsMsg';
            noResultsMsg.style.cssText = `
                text-align: center;
                padding: 2rem;
                font-size: 1.1rem;
                color: #666;
                display: none;
            `;
            noResultsMsg.textContent = 'No departments found matching your search.';
            departmentsGrid.parentNode.insertBefore(noResultsMsg, departmentsGrid.nextSibling);
            
            function performSearch() {
                const searchTerm = searchInput.value.toLowerCase().trim();
                const deptCards = departmentsGrid.querySelectorAll('.dept-card');
                let hasVisibleCards = false;
                
                deptCards.forEach(card => {
                    const deptName = card.querySelector('.dept-name').textContent.toLowerCase();
                    const deptCode = card.querySelector('.dept-code').textContent.toLowerCase();
                    
                    if (searchTerm === '' || deptName.includes(searchTerm) || deptCode.includes(searchTerm)) {
                        card.style.display = 'block';
                        hasVisibleCards = true;
                    } else {
                        card.style.display = 'none';
                    }
                });
                
                // Show/hide no results message
                noResultsMsg.style.display = (searchTerm !== '' && !hasVisibleCards) ? 'block' : 'none';
            }
            
            // Sort departments function
            function sortDepartments(sortBy, order) {
                const deptCards = Array.from(departmentsGrid.querySelectorAll('.dept-card'));
                
                deptCards.sort((a, b) => {
                    const aValue = parseFloat(a.dataset[sortBy]);
                    const bValue = parseFloat(b.dataset[sortBy]);
                    return order === 'desc' ? bValue - aValue : aValue - bValue;
                });
                
                // Re-append cards in new order
                deptCards.forEach(card => departmentsGrid.appendChild(card));
            }
            
            // Handle sort button clicks
            document.querySelectorAll('.sort-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const sortBy = this.dataset.sort;
                    const currentOrder = this.dataset.order;
                    const newOrder = currentOrder === 'desc' ? 'asc' : 'desc';
                    
                    // Update button state
                    this.dataset.order = newOrder;
                    this.classList.add('active');
                    this.querySelector('.sort-arrow').textContent = newOrder === 'desc' ? '↓' : '↑';
                    
                    // Reset other buttons
                    document.querySelectorAll('.sort-btn').forEach(otherBtn => {
                        if (otherBtn !== this) {
                            otherBtn.classList.remove('active');
                            otherBtn.dataset.order = 'desc';
                            otherBtn.querySelector('.sort-arrow').textContent = '↓';
                        }
                    });
                    
                    // Sort departments
                    sortDepartments(sortBy, newOrder);
                });
            });
            
            // Add event listeners
            searchInput.addEventListener('input', performSearch);
            searchInput.addEventListener('keyup', function(e) {
                if (e.key === 'Escape') {
                    searchInput.value = '';
                    performSearch();
                }
            });
            
            // Focus search on Cmd+K / Ctrl+K
            document.addEventListener('keydown', function(e) {
                if ((e.ctrlKey || e.metaKey) and e.key === 'k') {
                    e.preventDefault();
                    searchInput.focus();
                }
            });
            
            // Initial search to handle any pre-filled search terms
            performSearch();
            
            // Default sort by operating budget (descending)
            const operatingBtn = document.querySelector('.sort-btn[data-sort="operating"]');
            operatingBtn.dataset.order = 'desc';
            operatingBtn.querySelector('.sort-arrow').textContent = '↓';
            operatingBtn.classList.add('active');
            sortDepartments('operating', 'desc');
        });
    </script>
</body>
</html>
"""
        return html


def main():
    """Main function to run the departmental budget analyzer."""
    parser = argparse.ArgumentParser(description='Generate departmental budget reports')
    parser.add_argument('data_file', help='Path to budget allocations CSV file')
    parser.add_argument('--output-dir', '-o', 
                       default='data/output/departmental_reports',
                       help='Output directory for HTML reports')
    
    args = parser.parse_args()
    
    # Create analyzer and generate reports
    analyzer = DepartmentalBudgetAnalyzer(args.data_file, args.output_dir)
    analyzer.generate_all_reports()
    
    logger.info(f"All reports generated successfully in {args.output_dir}")
    logger.info("Open index.html to view all department reports")


if __name__ == "__main__":
    main()
