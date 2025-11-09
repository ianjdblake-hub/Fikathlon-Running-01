#!/usr/bin/env python3
"""
Österlen Spring Trail 60km Training Analyzer - HTML Report Version
Analyzes Garmin Connect data and generates interactive HTML reports
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import webbrowser

class HTMLTrainingAnalyzer:
    def __init__(self, csv_file):
        """Initialize with Garmin CSV export"""
        self.df = pd.read_csv(csv_file)
        self.df['Date'] = pd.to_datetime(self.df['Date'])
        self.df = self.df.sort_values('Date')
        
        # Marathon date for reference
        self.marathon_date = pd.to_datetime('2025-10-12')
        self.race_date = pd.to_datetime('2026-04-26')  # Österlen Spring Trail
        
        # Clean numeric columns
        self._clean_data()
        
    def _clean_data(self):
        """Clean and convert data types"""
        # Remove commas from numbers
        self.df['Distance'] = self.df['Distance'].astype(str).str.replace(',', '').astype(float)
        self.df['Calories'] = self.df['Calories'].astype(str).str.replace(',', '').astype(float)
        
        # Convert time to minutes
        def time_to_minutes(time_str):
            try:
                if pd.isna(time_str):
                    return 0
                parts = str(time_str).split(':')
                if len(parts) == 3:
                    h, m, s = parts
                    return int(h) * 60 + int(m) + float(s) / 60
                elif len(parts) == 2:
                    m, s = parts
                    return int(m) + float(s) / 60
                return 0
            except:
                return 0
        
        self.df['Time_Minutes'] = self.df['Time'].apply(time_to_minutes)
        
        # Fill NaN elevations with 0
        self.df['Total Ascent'] = pd.to_numeric(self.df['Total Ascent'], errors='coerce').fillna(0)
        self.df['Total Descent'] = pd.to_numeric(self.df['Total Descent'], errors='coerce').fillna(0)
        
    def get_running_data(self):
        """Filter for running activities only"""
        return self.df[self.df['Activity Type'] == 'Running'].copy()
    
    def _get_weekly_data(self, weeks=4):
        """Get weekly aggregated data for charts"""
        running = self.get_running_data()
        cutoff_date = running['Date'].max() - timedelta(days=weeks*7)
        recent = running[running['Date'] >= cutoff_date].copy()
        
        recent['Week'] = recent['Date'].dt.to_period('W')
        weekly = recent.groupby('Week').agg({
            'Distance': 'sum',
            'Total Ascent': 'sum',
            'Time_Minutes': 'sum',
            'Activity Type': 'count',
            'Avg HR': 'mean',
            'Aerobic TE': 'sum'
        }).round(1)
        
        return weekly
    
    def _get_chart_data(self):
        """Prepare data for JavaScript charts"""
        weekly = self._get_weekly_data(weeks=8)
        
        weeks = [str(w) for w in weekly.index]
        distances = weekly['Distance'].tolist()
        elevations = weekly['Total Ascent'].tolist()
        
        return {
            'weeks': weeks,
            'distances': distances,
            'elevations': elevations
        }
    
    def generate_html_report(self, current_week_of_plan=1, output_file='training_report.html'):
        """Generate complete HTML report"""
        running = self.get_running_data()
        
        # Get all analysis data
        days_since_marathon = (running['Date'].max() - self.marathon_date).days
        weeks_since = days_since_marathon / 7
        
        # Post-marathon stats
        post_marathon = running[running['Date'] > self.marathon_date]
        post_marathon_runs = len(post_marathon)
        post_marathon_distance = post_marathon['Distance'].sum()
        post_marathon_avg = post_marathon['Distance'].mean() if len(post_marathon) > 0 else 0
        
        # Recovery status
        if weeks_since < 2:
            recovery_status = "EARLY RECOVERY"
            recovery_class = "warning"
        elif weeks_since < 4:
            recovery_status = "RECOVERY PHASE"
            recovery_class = "warning"
        else:
            recovery_status = "RECOVERED"
            recovery_class = "success"
        
        # Recent 4 weeks analysis
        recent_4wks = running[running['Date'] >= running['Date'].max() - timedelta(days=28)]
        total_distance = recent_4wks['Distance'].sum()
        total_elevation = recent_4wks['Total Ascent'].sum()
        total_runs = len(recent_4wks)
        avg_distance = total_distance / total_runs if total_runs > 0 else 0
        avg_weekly_dist = total_distance / 4
        avg_weekly_elev = total_elevation / 4
        
        # Last 7 days
        last_week_end = running['Date'].max()
        last_week_start = last_week_end - timedelta(days=7)
        last_week = running[(running['Date'] >= last_week_start) & 
                           (running['Date'] <= last_week_end)]
        
        week_distance = last_week['Distance'].sum()
        week_elevation = last_week['Total Ascent'].sum()
        week_runs = len(last_week)
        
        # Training plan targets
        plan_targets = {
            1: {'distance': 35, 'elevation': 200, 'runs': 4},
            2: {'distance': 38, 'elevation': 250, 'runs': 4},
            3: {'distance': 42, 'elevation': 280, 'runs': 4},
            4: {'distance': 45, 'elevation': 300, 'runs': 4},
            5: {'distance': 45, 'elevation': 400, 'runs': 4},
            6: {'distance': 48, 'elevation': 450, 'runs': 4},
            7: {'distance': 52, 'elevation': 550, 'runs': 4},
            8: {'distance': 55, 'elevation': 600, 'runs': 4},
            9: {'distance': 52, 'elevation': 650, 'runs': 4},
            10: {'distance': 56, 'elevation': 700, 'runs': 4},
            11: {'distance': 60, 'elevation': 850, 'runs': 5},
            12: {'distance': 60, 'elevation': 900, 'runs': 5},
            13: {'distance': 55, 'elevation': 750, 'runs': 4},
            14: {'distance': 48, 'elevation': 600, 'runs': 4},
        }
        
        target = plan_targets.get(current_week_of_plan, {'distance': 40, 'elevation': 300, 'runs': 4})
        
        dist_pct = (week_distance / target['distance']) * 100 if target['distance'] > 0 else 0
        elev_pct = (week_elevation / target['elevation']) * 100 if target['elevation'] > 0 else 0
        runs_pct = (week_runs / target['runs']) * 100 if target['runs'] > 0 else 0
        
        # Assessment
        if dist_pct >= 90 and elev_pct >= 80:
            assessment = "ON TRACK"
            assessment_class = "success"
            assessment_icon = "✓"
        elif dist_pct >= 75:
            assessment = "SLIGHTLY BEHIND"
            assessment_class = "warning"
            assessment_icon = "△"
        else:
            assessment = "BEHIND TARGET"
            assessment_class = "danger"
            assessment_icon = "⚠"
        
        # HR analysis
        recent_10 = running.tail(10)
        avg_hr = recent_10['Avg HR'].mean() if 'Avg HR' in recent_10.columns else 0
        max_hr = recent_10['Max HR'].mean() if 'Max HR' in recent_10.columns else 0
        
        if 'Aerobic TE' in recent_10.columns:
            avg_te = recent_10['Aerobic TE'].mean()
            if avg_te > 4.0:
                load_status = "HIGH LOAD"
                load_class = "danger"
            elif avg_te > 3.0:
                load_status = "MODERATE LOAD"
                load_class = "success"
            else:
                load_status = "LOW LOAD"
                load_class = "warning"
        else:
            avg_te = 0
            load_status = "N/A"
            load_class = "secondary"
        
        # Race countdown
        days_to_race = (self.race_date - datetime.now()).days
        weeks_to_race = days_to_race / 7
        
        # Phase info
        if current_week_of_plan <= 4:
            phase = "BASE BUILDING"
            phase_focus = "Rebuild volume gradually, introduce hill work"
        elif current_week_of_plan <= 8:
            phase = "HILL STRENGTH"
            phase_focus = "Progressive hill intervals, downhill practice"
        elif current_week_of_plan <= 14:
            phase = "SPECIFIC ENDURANCE"
            phase_focus = "Long runs with elevation, tempo on hills"
        elif current_week_of_plan <= 18:
            phase = "RACE SIMULATION"
            phase_focus = "Race-pace efforts, practice nutrition"
        else:
            phase = "TAPER"
            phase_focus = "Maintain intensity, reduce volume"
        
        # Get chart data
        chart_data = self._get_chart_data()
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Training Report - Week {current_week_of_plan}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            border-left: 4px solid #667eea;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }}
        
        .stat-label {{
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            line-height: 1;
        }}
        
        .stat-unit {{
            font-size: 0.5em;
            color: #999;
            font-weight: normal;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .badge.success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .badge.warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .badge.danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .badge.secondary {{
            background: #e2e3e5;
            color: #383d41;
        }}
        
        .progress-container {{
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
            height: 30px;
            position: relative;
        }}
        
        .progress-bar {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            transition: width 1s ease;
        }}
        
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .comparison-table th,
        .comparison-table td {{
            padding: 15px;
            text-align: left;
        }}
        
        .comparison-table th {{
            background: #667eea;
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 0.5px;
        }}
        
        .comparison-table tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        .comparison-table tr:hover {{
            background: #e9ecef;
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
            margin: 30px 0;
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .alert {{
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid;
        }}
        
        .alert.success {{
            background: #d4edda;
            border-color: #28a745;
            color: #155724;
        }}
        
        .alert.warning {{
            background: #fff3cd;
            border-color: #ffc107;
            color: #856404;
        }}
        
        .alert.info {{
            background: #d1ecf1;
            border-color: #17a2b8;
            color: #0c5460;
        }}
        
        .recommendations {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin: 30px 0;
        }}
        
        .recommendations h3 {{
            margin-bottom: 15px;
            font-size: 1.5em;
        }}
        
        .recommendations ul {{
            list-style: none;
            padding: 0;
        }}
        
        .recommendations li {{
            padding: 10px 0;
            padding-left: 30px;
            position: relative;
        }}
        
        .recommendations li:before {{
            content: "→";
            position: absolute;
            left: 0;
            font-weight: bold;
            font-size: 1.2em;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            background: #f8f9fa;
            color: #666;
            font-size: 0.9em;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
            }}
            .stat-card:hover {{
                transform: none;
            }}
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            .header h1 {{
                font-size: 1.8em;
            }}
            .content {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏃‍♂️ Training Analysis Report</h1>
            <p>Österlen Spring Trail 60km Preparation</p>
            <p style="margin-top: 10px; font-size: 1em;">Week {current_week_of_plan} of 22 • {phase}</p>
        </div>
        
        <div class="content">
            <!-- Race Countdown -->
            <div class="alert info">
                <strong>🎯 Race Countdown:</strong> {days_to_race} days ({weeks_to_race:.0f} weeks) until Österlen Spring Trail 60km
            </div>
            
            <!-- Key Stats -->
            <div class="section">
                <h2 class="section-title">📊 Key Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">Weekly Distance</div>
                        <div class="stat-value">{avg_weekly_dist:.1f} <span class="stat-unit">km</span></div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Weekly Elevation</div>
                        <div class="stat-value">{avg_weekly_elev:.0f} <span class="stat-unit">m</span></div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Runs (4 weeks)</div>
                        <div class="stat-value">{total_runs}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Average HR</div>
                        <div class="stat-value">{avg_hr:.0f} <span class="stat-unit">bpm</span></div>
                    </div>
                </div>
            </div>
            
            <!-- Marathon Recovery -->
            <div class="section">
                <h2 class="section-title">🏃 Marathon Recovery Status</h2>
                <p><strong>Marathon Date:</strong> {self.marathon_date.date()}</p>
                <p><strong>Days Since Marathon:</strong> {days_since_marathon} days ({weeks_since:.1f} weeks)</p>
                <p><strong>Marathon Time:</strong> 4:10:00</p>
                <p style="margin-top: 15px;"><strong>Status:</strong> <span class="badge {recovery_class}">{recovery_status}</span></p>
                <p style="margin-top: 10px;"><strong>Post-Marathon Running:</strong> {post_marathon_runs} runs, {post_marathon_distance:.1f} km total (avg {post_marathon_avg:.1f} km/run)</p>
            </div>
            
            <!-- Week Progress -->
            <div class="section">
                <h2 class="section-title">🎯 Week {current_week_of_plan} Progress vs Plan</h2>
                
                <table class="comparison-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Actual</th>
                            <th>Target</th>
                            <th>Progress</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Distance (km)</strong></td>
                            <td>{week_distance:.1f} km</td>
                            <td>{target['distance']} km</td>
                            <td>
                                <div class="progress-container">
                                    <div class="progress-bar" style="width: {min(dist_pct, 100):.0f}%">{dist_pct:.0f}%</div>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td><strong>Elevation (m)</strong></td>
                            <td>{week_elevation:.0f} m</td>
                            <td>{target['elevation']} m</td>
                            <td>
                                <div class="progress-container">
                                    <div class="progress-bar" style="width: {min(elev_pct, 100):.0f}%">{elev_pct:.0f}%</div>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td><strong>Number of Runs</strong></td>
                            <td>{week_runs}</td>
                            <td>{target['runs']}</td>
                            <td>
                                <div class="progress-container">
                                    <div class="progress-bar" style="width: {min(runs_pct, 100):.0f}%">{runs_pct:.0f}%</div>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
                
                <div class="alert {assessment_class}" style="margin-top: 20px;">
                    <strong>{assessment_icon} Assessment:</strong> {assessment}
                </div>
            </div>
            
            <!-- Charts -->
            <div class="section">
                <h2 class="section-title">📈 Training Trends (Last 8 Weeks)</h2>
                <div class="chart-container">
                    <canvas id="distanceChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="elevationChart"></canvas>
                </div>
            </div>
            
            <!-- HR Analysis -->
            <div class="section">
                <h2 class="section-title">❤️ Heart Rate & Recovery</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">Avg HR (last 10 runs)</div>
                        <div class="stat-value">{avg_hr:.0f} <span class="stat-unit">bpm</span></div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Avg Max HR</div>
                        <div class="stat-value">{max_hr:.0f} <span class="stat-unit">bpm</span></div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Training Load</div>
                        <div class="stat-value">{avg_te:.1f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Load Status</div>
                        <div class="stat-value" style="font-size: 1.2em;"><span class="badge {load_class}">{load_status}</span></div>
                    </div>
                </div>
            </div>
            
            <!-- Recommendations -->
            <div class="recommendations">
                <h3>💡 Recommendations for Next Week</h3>
                <p style="margin-bottom: 15px;"><strong>Current Phase:</strong> {phase}</p>
                <p style="margin-bottom: 15px;"><strong>Focus:</strong> {phase_focus}</p>
                <ul>
                    <li>Target weekly distance: {plan_targets.get(current_week_of_plan + 1, {}).get('distance', 40)} km</li>
                    <li>Target elevation gain: {plan_targets.get(current_week_of_plan + 1, {}).get('elevation', 300)} m</li>
                    <li>Use your 22km work commute for long run</li>
                    <li>Maintain weekly gym session (squats, lunges, Nordic curls)</li>
                    <li>Practice race nutrition on runs &gt;90 minutes</li>
                    <li>Use stair machine 2-3x per week for elevation work</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Österlen Spring Trail 60km Training Analysis • Week {current_week_of_plan} of 22</p>
        </div>
    </div>
    
    <script>
        // Distance Chart
        const distanceCtx = document.getElementById('distanceChart').getContext('2d');
        new Chart(distanceCtx, {{
            type: 'line',
            data: {{
                labels: {chart_data['weeks']},
                datasets: [{{
                    label: 'Weekly Distance (km)',
                    data: {chart_data['distances']},
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    title: {{
                        display: true,
                        text: 'Weekly Distance Trend',
                        font: {{
                            size: 16,
                            weight: 'bold'
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Distance (km)'
                        }}
                    }}
                }}
            }}
        }});
        
        // Elevation Chart
        const elevationCtx = document.getElementById('elevationChart').getContext('2d');
        new Chart(elevationCtx, {{
            type: 'bar',
            data: {{
                labels: {chart_data['weeks']},
                datasets: [{{
                    label: 'Weekly Elevation (m)',
                    data: {chart_data['elevations']},
                    backgroundColor: 'rgba(118, 75, 162, 0.8)',
                    borderColor: '#764ba2',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    title: {{
                        display: true,
                        text: 'Weekly Elevation Gain',
                        font: {{
                            size: 16,
                            weight: 'bold'
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Elevation (m)'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        # Write HTML file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python training_analyzer_html.py <garmin_activities.csv> [week_number] [--output filename.html]")
        print("\nExample: python training_analyzer_html.py Activities.csv 5")
        print("  (where 5 is the current week of your training plan)")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    current_week = 1
    output_file = 'training_report.html'
    
    # Parse arguments
    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == '--output' and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
        elif arg.isdigit():
            current_week = int(arg)
    
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    
    print(f"Analyzing training data...")
    analyzer = HTMLTrainingAnalyzer(csv_file)
    
    print(f"Generating HTML report for Week {current_week}...")
    output_path = analyzer.generate_html_report(current_week_of_plan=current_week, output_file=output_file)
    
    print(f"\n✅ Report generated successfully: {output_path}")
    print(f"\nOpening in your default browser...")
    
    # Open in browser
    webbrowser.open('file://' + os.path.abspath(output_path))
    
    print(f"\n📄 You can also manually open: {os.path.abspath(output_path)}")
    print(f"📧 Share, print, or save as PDF from your browser!")

if __name__ == "__main__":
    main()
