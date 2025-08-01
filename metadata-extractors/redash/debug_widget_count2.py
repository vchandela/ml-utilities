#!/usr/bin/env python3
"""
Debug Widget Details for Specific Dashboard

Detailed analysis of individual widgets in the Web-Led iOS Marketing dashboard
showing widget names, types, and actual query text.
"""

import os
import asyncio
from dotenv import load_dotenv
from metadata import RedashMetadataExtractor

load_dotenv()

async def debug_dashboard_widgets():
    """Detailed analysis of widgets in the Web-Led iOS Marketing dashboard"""
    
    credentials = {
        'api_url': os.getenv('REDASH_API_URL'),
        'api_key': os.getenv('REDASH_API_KEY')
    }
    
    extractor = RedashMetadataExtractor(credentials)
    
    # Test connection and get version
    await extractor.test_connection()
    await extractor._detect_version()
    
    # Target dashboard details
    dashboard_slug = "web-led-ios-marketing"
    dashboard_id = 213
    
    print(f"🔄 Fetching details for dashboard: {dashboard_slug} (ID: {dashboard_id})")
    
    # Get the specific dashboard details
    use_slug = extractor._should_use_slug()
    if use_slug:
        dashboard_details = await extractor.get_dashboard_details(dashboard_slug)
    else:
        dashboard_details = await extractor.get_dashboard_details(str(dashboard_id))
    
    if not dashboard_details:
        print(f"❌ Could not fetch dashboard details")
        return
    
    # Prepare output lines
    output_lines = []
    output_lines.append("Detailed Widget Analysis: Web-Led iOS Marketing Dashboard")
    output_lines.append("=" * 80)
    output_lines.append(f"Dashboard Name: {dashboard_details.get('name', 'Unknown')}")
    output_lines.append(f"Dashboard ID: {dashboard_details.get('id', 'Unknown')}")
    output_lines.append(f"Dashboard Slug: {dashboard_details.get('slug', 'Unknown')}")
    output_lines.append(f"Dashboard Description: {dashboard_details.get('description', 'No description')}")
    output_lines.append("")
    
    widgets = dashboard_details.get('widgets', [])
    output_lines.append(f"Total Widgets: {len(widgets)}")
    output_lines.append("")
    
    # Process each widget
    widgets_with_queries = 0
    
    for i, widget in enumerate(widgets, 1):
        widget_id = widget.get('id', 'Unknown')
        visualization = widget.get('visualization', {})
        
        # Get widget name and type
        widget_name = "Unnamed Widget"
        widget_type = "text"
        
        if visualization:
            widget_name = visualization.get('name', 'Unnamed Widget')
            widget_type = visualization.get('type', 'unknown')
        
        # Check if widget has a query
        query_id = visualization.get("query", {}).get("id") if visualization else None
        
        output_lines.append(f"Widget {i}:")
        output_lines.append(f"  Widget ID: {widget_id}")
        output_lines.append(f"  Widget Name: {widget_name}")
        output_lines.append(f"  Widget Type: {widget_type}")
        
        if query_id:
            widgets_with_queries += 1
            output_lines.append(f"  Query ID: {query_id}")
            
            # Fetch the query details
            try:
                query_data = await extractor.get_query(str(query_id))
                
                if query_data:
                    query_text = query_data.get('query', 'No query text available')
                    query_name = query_data.get('name', 'Unnamed Query')
                    query_description = query_data.get('description', 'No description')
                    data_source = query_data.get('data_source_id', 'Unknown data source')
                    
                    # Handle data source if it's a dict
                    if isinstance(data_source, dict):
                        data_source = data_source.get('name', 'Unknown data source')
                    
                    output_lines.append(f"  Query Name: {query_name}")
                    output_lines.append(f"  Query Description: {query_description}")
                    output_lines.append(f"  Data Source: {data_source}")
                    output_lines.append(f"  Query Text:")
                    
                    # Format query text with indentation
                    query_lines = str(query_text).split('\n')
                    for query_line in query_lines:
                        output_lines.append(f"    {query_line}")
                else:
                    output_lines.append(f"  ❌ Could not fetch query details")
                    
            except Exception as e:
                output_lines.append(f"  ❌ Error fetching query: {str(e)}")
        else:
            output_lines.append(f"  No Query (text widget or other non-query widget)")
        
        output_lines.append("")  # Blank line between widgets
    
    # Add summary
    output_lines.append("=" * 80)
    output_lines.append("SUMMARY")
    output_lines.append("=" * 80)
    output_lines.append(f"Total Widgets: {len(widgets)}")
    output_lines.append(f"Widgets with Queries: {widgets_with_queries}")
    output_lines.append(f"Widgets without Queries: {len(widgets) - widgets_with_queries}")
    
    # Write to test2.txt
    with open('test2.txt', 'w') as f:
        for line in output_lines:
            f.write(line + '\n')
    
    print(f"✅ Detailed analysis complete! Results written to test2.txt")
    print(f"📊 Summary: {len(widgets)} widgets, {widgets_with_queries} with queries")

if __name__ == "__main__":
    asyncio.run(debug_dashboard_widgets()) 