#!/usr/bin/env python3
"""
Debug Widget Counting

Detailed analysis of widget counting to understand why we get 2086 instead of ~663
"""

import os
import asyncio
from dotenv import load_dotenv
from metadata import RedashMetadataExtractor

load_dotenv()

async def debug_widget_counting():
    """Detailed analysis of widget counting"""
    
    credentials = {
        'api_url': os.getenv('REDASH_API_URL'),
        'api_key': os.getenv('REDASH_API_KEY')
    }
    
    extractor = RedashMetadataExtractor(credentials)
    
    print("🔍 Debugging Widget Counting")
    print("="*50)
    
    # Test connection and get version
    await extractor.test_connection()
    await extractor._detect_version()
    
    # Get dashboards
    dashboards = await extractor.get_dashboards()
    print(f"📊 Total dashboards in list: {len(dashboards)}")
    
    # Get dashboard details with version-appropriate IDs
    use_slug = extractor._should_use_slug()
    print(f"🏷️  Using {'slug' if use_slug else 'numeric ID'} identifiers")
    
    # Get all dashboard details
    print(f"\n🔄 Fetching dashboard details...")
    dashboard_details = await asyncio.gather(
        *[extractor._get_dashboard_with_id(dashboard, use_slug) for dashboard in dashboards],
        return_exceptions=True
    )
    
    valid_dashboards = [d for d in dashboard_details if d and not isinstance(d, Exception)]
    print(f"✅ Accessible dashboards: {len(valid_dashboards)}/{len(dashboards)}")
    
    # Analyze widget patterns
    total_widgets = 0
    widgets_with_viz = 0
    widgets_with_query_id = 0
    widget_types = {}
    sample_widgets = []
    
    for i, dashboard in enumerate(valid_dashboards):
        if not dashboard or not isinstance(dashboard, dict) or 'widgets' not in dashboard:
            continue
            
        dashboard_widgets = dashboard['widgets']
        total_widgets += len(dashboard_widgets)
        
        for widget in dashboard_widgets:
            # Count widgets with visualization
            if widget.get('visualization'):
                widgets_with_viz += 1
                
            # Count widgets with query IDs
            visualization = widget.get("visualization", {})
            query_id = visualization.get("query", {}).get("id") if visualization else None
            
            if query_id:
                widgets_with_query_id += 1
                
            # Track widget types
            widget_type = "text"  # default
            if visualization:
                widget_type = visualization.get("type", "unknown")
            widget_types[widget_type] = widget_types.get(widget_type, 0) + 1
            
            # Collect samples for first few dashboards
            if i < 3 and len(sample_widgets) < 10:
                sample_widgets.append({
                    'dashboard_id': dashboard.get('id'),
                    'widget_id': widget.get('id'),
                    'has_viz': bool(widget.get('visualization')),
                    'viz_type': widget_type,
                    'has_query_id': bool(query_id),
                    'query_id': query_id
                })
    
    print(f"\n📊 Widget Analysis:")
    print(f"   - Total widgets across all dashboards: {total_widgets}")
    print(f"   - Widgets with visualization: {widgets_with_viz}")
    print(f"   - Widgets with query_id: {widgets_with_query_id}")
    print(f"   - Expected count: ~663")
    print(f"   - Current count: {widgets_with_query_id}")
    print(f"   - Ratio: {widgets_with_query_id/663:.1f}x higher than expected")
    
    print(f"\n📊 Widget Types:")
    for widget_type, count in sorted(widget_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {widget_type}: {count}")
    
    print(f"\n🔍 Sample Widgets (first 10):")
    for widget in sample_widgets:
        print(f"   - Dashboard {widget['dashboard_id']}, Widget {widget['widget_id']}: "
              f"type={widget['viz_type']}, has_query={widget['has_query_id']}, query_id={widget['query_id']}")
    
    # Check if there are duplicate query IDs (widgets sharing queries)
    all_query_ids = []
    for dashboard in valid_dashboards:
        if not dashboard or not isinstance(dashboard, dict) or 'widgets' not in dashboard:
            continue
        for widget in dashboard['widgets']:
            visualization = widget.get("visualization", {})
            query_id = visualization.get("query", {}).get("id") if visualization else None
            if query_id:
                all_query_ids.append(query_id)
    
    unique_queries = len(set(all_query_ids))
    print(f"\n🔗 Query Sharing Analysis:")
    print(f"   - Total widget-query pairs: {len(all_query_ids)}")
    print(f"   - Unique queries: {unique_queries}")
    print(f"   - Avg widgets per query: {len(all_query_ids)/unique_queries:.1f}")

if __name__ == "__main__":
    asyncio.run(debug_widget_counting()) 