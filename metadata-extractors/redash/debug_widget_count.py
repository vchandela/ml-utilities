#!/usr/bin/env python3
"""
Debug Widget Counting

Detailed analysis of widget counting per dashboard to understand distribution
"""

import os
import asyncio
from dotenv import load_dotenv
from metadata import RedashMetadataExtractor

load_dotenv()

async def debug_widget_counting():
    """Detailed analysis of widget counting per dashboard"""
    
    credentials = {
        'api_url': os.getenv('REDASH_API_URL'),
        'api_key': os.getenv('REDASH_API_KEY')
    }
    
    extractor = RedashMetadataExtractor(credentials)
    
    # Test connection and get version
    await extractor.test_connection()
    await extractor._detect_version()
    
    # Get dashboards
    dashboards = await extractor.get_dashboards()
    
    # Get dashboard details with version-appropriate IDs
    use_slug = extractor._should_use_slug()
    
    # Get all dashboard details
    dashboard_details = await asyncio.gather(
        *[extractor._get_dashboard_with_id(dashboard, use_slug) for dashboard in dashboards],
        return_exceptions=True
    )
    
    valid_dashboards = [d for d in dashboard_details if d and not isinstance(d, Exception)]
    
    # Prepare output lines
    output_lines = []
    output_lines.append("Dashboard Widget Analysis")
    output_lines.append("=" * 80)
    output_lines.append(f"Total Dashboards: {len(dashboards)}")
    output_lines.append(f"Accessible Dashboards: {len(valid_dashboards)}")
    output_lines.append("")
    
    # Analyze each dashboard
    total_widgets_across_all = 0
    total_widget_types = {}
    
    for dashboard in valid_dashboards:
        if not dashboard or not isinstance(dashboard, dict) or 'widgets' not in dashboard:
            continue
            
        dashboard_name = dashboard.get('name', 'Unnamed Dashboard')
        dashboard_id = dashboard.get('id', 'Unknown ID')
        dashboard_slug = dashboard.get('slug', 'no-slug')
        dashboard_widgets = dashboard['widgets']
        
        # Count widgets by type for this dashboard
        dashboard_widget_types = {}
        widgets_with_queries = 0
        
        for widget in dashboard_widgets:
            # Count widgets with query IDs
            visualization = widget.get("visualization", {})
            query_id = visualization.get("query", {}).get("id") if visualization else None
            
            if query_id:
                widgets_with_queries += 1
                
            # Track widget types
            widget_type = "text"  # default
            if visualization:
                widget_type = visualization.get("type", "unknown")
            
            # Count for this dashboard
            dashboard_widget_types[widget_type] = dashboard_widget_types.get(widget_type, 0) + 1
            
            # Count for overall totals
            total_widget_types[widget_type] = total_widget_types.get(widget_type, 0) + 1
        
        total_widgets_across_all += len(dashboard_widgets)
        
        # Add dashboard info to output
        output_lines.append(f"Dashboard: {dashboard_name}")
        output_lines.append(f"  ID: {dashboard_id}, Slug: {dashboard_slug}")
        output_lines.append(f"  Total Widgets: {len(dashboard_widgets)}")
        output_lines.append(f"  Widgets with Queries: {widgets_with_queries}")
        
        if dashboard_widget_types:
            output_lines.append(f"  Widget Types:")
            for widget_type, count in sorted(dashboard_widget_types.items(), key=lambda x: x[1], reverse=True):
                output_lines.append(f"    - {widget_type}: {count}")
        else:
            output_lines.append(f"  No widgets found")
        
        output_lines.append("")  # Blank line between dashboards
    
    # Add summary
    output_lines.append("=" * 80)
    output_lines.append("SUMMARY")
    output_lines.append("=" * 80)
    output_lines.append(f"Total Widgets Across All Dashboards: {total_widgets_across_all}")
    output_lines.append("")
    output_lines.append("Overall Widget Type Distribution:")
    for widget_type, count in sorted(total_widget_types.items(), key=lambda x: x[1], reverse=True):
        output_lines.append(f"  - {widget_type}: {count}")
    
    # Write to test.txt
    with open('test.txt', 'w') as f:
        for line in output_lines:
            f.write(line + '\n')
    
    print(f"✅ Analysis complete! Results written to test.txt")
    print(f"📊 Summary: {len(valid_dashboards)} dashboards, {total_widgets_across_all} total widgets")

if __name__ == "__main__":
    asyncio.run(debug_widget_counting()) 