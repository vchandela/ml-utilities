#!/usr/bin/env python3
"""
Redash Golden Asset Ranking System - Main Entry Point

Entry point for testing Phase 1: Foundational Layer - High-Performance Data Extraction
"""

import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the metadata extractor
# Import the metadata extractor
try:
    from .metadata import RedashMetadataExtractor
except ImportError:
    from metadata import RedashMetadataExtractor


async def main():
    """Main function to test Phase 1 implementation"""
    try:
        # Load credentials from environment variables
        api_url = os.getenv('REDASH_API_URL')
        api_key = os.getenv('REDASH_API_KEY')
        
        if not all([api_url, api_key]):
            print("❌ Missing required environment variables:")
            print("   Please set REDASH_API_URL and REDASH_API_KEY")
            print("   in your .env file or environment variables.")
            return
        
        print("🔧 Redash Golden Asset Ranking System")
        print("="*50)
        print("Phase 1: Foundational Layer - High-Performance Data Extraction")
        print("="*50)
        print(f"🌐 Redash URL: {api_url}")
        api_key_display = api_key
        if api_key_display and len(api_key_display) > 4:
            api_key_display = '*' * (len(api_key_display) - 4) + api_key_display[-4:]
        print(f"🔑 API Key: {api_key_display}")
        print()
        
        print("🔄 Starting Phase 1 extraction...")
        start_time = datetime.now()
        
        # Initialize extractor and run Phase 1
        extractor = RedashMetadataExtractor(api_url, api_key)
        results = await extractor.extract_all_metadata()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if "error" in results:
            print(f"❌ {results['error']}")
            return
            
        print("✅ Phase 1 completed in {:.2f} seconds!".format(duration))
        
        # Print the summary
        print("\n📊 Phase 1 Results:")
        print("   🔗 Connection: {}".format(results['connection_test']['message']))
        print("   🏷️  Version: {} (slug mode: {})".format(results['version'], results['use_slug_for_dashboards']))
        print("\n📈 Data Extraction:")
        counts = results.get('counts', {})
        print(f"   - Total Dashboards: {counts.get('dashboards', 0)}")
        print(f"   - Detailed Dashboards: {counts.get('detailed_dashboards', 0)}")
        print(f"   - Total Queries: {counts.get('queries', 0)}")
        print(f"   - Detailed Queries: {counts.get('detailed_queries', 0)}")
        
        print("\n🔗 Dependency Mapping:")
        deps = results.get('dependency_maps', {})
        print(f"   - Queries with dashboard dependencies: {deps.get('queries_with_dashboard_deps', 0)}")
        print(f"   - Queries with chart widgets: {deps.get('queries_with_chart_widgets', 0)}")
        print(f"   - Dashboards with queries: {deps.get('dashboards_with_queries', 0)}")
        
        print("\n🎉 Phase 1 foundation is ready for scoring phases!")
        
        # Phase 2: Golden Saved Query Scoring Logic
        print("\n" + "="*50)
        print("🔄 Starting Phase 2: Golden Saved Query Scoring Logic...")
        
        phase2_start = datetime.now()
        scored_queries = extractor.score_all_queries()
        phase2_duration = (datetime.now() - phase2_start).total_seconds()
        
        print("✅ Phase 2 completed in {:.2f} seconds!".format(phase2_duration))
        
        if scored_queries:
            print("\n📊 Phase 2 Query Scoring Results:")
            print(f"   - Total Scored Queries: {len(scored_queries)}")
            
            # Show top 5 queries
            print("   \n🏆 Top 5 Golden Queries:")
            for i, query in enumerate(scored_queries[:5], 1):
                print(f"      {i}. {query['name'][:50]}{'...' if len(query['name']) > 50 else ''}")
                print(f"         Golden Score: {query['golden_query_score']:.2f} "
                      f"(Impact: {query['impact_score']:.2f}, "
                      f"Recency: {query['recency_score']:.2f}, "
                      f"Curation: {query['curation_score']:.2f})")
                print(f"         Dashboards: {query['downstream_dashboard_count']}, "
                      f"Charts: {query['downstream_chart_count']}")
                print()
            
            # Show score distribution
            scores = [q['golden_query_score'] for q in scored_queries]
            if scores:
                print("   📈 Score Distribution:")
                print(f"      - Highest: {max(scores):.2f}")
                print(f"      - Average: {sum(scores)/len(scores):.2f}")
                print(f"      - Lowest: {min(scores):.2f}")
        
        # Phase 3: Golden Dashboard Scoring Logic
        print("\n" + "="*50)
        print("🔄 Starting Phase 3: Golden Dashboard Scoring Logic...")
        
        phase3_start = datetime.now()
        scored_dashboards = extractor.score_all_dashboards(scored_queries)
        phase3_duration = (datetime.now() - phase3_start).total_seconds()
        
        print("✅ Phase 3 completed in {:.2f} seconds!".format(phase3_duration))
        
        if scored_dashboards:
            print("\n📊 Phase 3 Dashboard Scoring Results:")
            print(f"   - Total Scored Dashboards: {len(scored_dashboards)}")
            
            # Show top 5 dashboards
            print("   \n🏆 Top 5 Golden Dashboards:")
            for i, dashboard in enumerate(scored_dashboards[:5], 1):
                print(f"      {i}. {dashboard['name'][:50]}{'...' if len(dashboard['name']) > 50 else ''}")
                print(f"         Golden Score: {dashboard['golden_dashboard_score']:.2f} "
                      f"(Content: {dashboard['content_quality_score']:.2f}, "
                      f"Recency: {dashboard['recency_score']:.2f}, "
                      f"Curation: {dashboard['curation_score']:.2f})")
                # Count queries used by this dashboard
                query_count = len(extractor.dashboard_to_queries_map.get(dashboard['id'], set()))
                print(f"         Queries Used: {query_count}, "
                      f"Is Draft: {dashboard.get('is_draft', False)}")
                print()
            
            # Show score distribution
            dashboard_scores = [d['golden_dashboard_score'] for d in scored_dashboards]
            if dashboard_scores:
                print("   📈 Dashboard Score Distribution:")
                print(f"      - Highest: {max(dashboard_scores):.2f}")
                print(f"      - Average: {sum(dashboard_scores)/len(dashboard_scores):.2f}")
                print(f"      - Lowest: {min(dashboard_scores):.2f}")
        
        # Save combined results for all phases
        combined_results = {
            "phase1": results,
            "phase2": {
                "scored_queries_count": len(scored_queries),
                "execution_time": phase2_duration,
                "top_5_queries": scored_queries[:5] if scored_queries else []
            },
            "phase3": {
                "scored_dashboards_count": len(scored_dashboards),
                "execution_time": phase3_duration,
                "top_5_dashboards": scored_dashboards[:5] if scored_dashboards else []
            }
        }
        
        with open('phase1_2_3_results.json', 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, indent=2, default=str)
        print("\n💾 Combined results saved to phase1_2_3_results.json")
        
        # Phase 4: Final Output Generation
        print("\n" + "="*50)
        print("🔄 Starting Phase 4: Final Output Generation...")
        
        phase4_start = datetime.now()
        try:
            generated_files = extractor.generate_outputs(scored_queries, scored_dashboards)
            phase4_duration = (datetime.now() - phase4_start).total_seconds()
            
            print("✅ Phase 4 completed in {:.2f} seconds!".format(phase4_duration))
            
            if generated_files:
                print("\n📊 Phase 4 Output Generation Results:")
                print("   📁 Generated Files:")
                for file_type, file_path in generated_files.items():
                    file_name = os.path.basename(file_path)
                    print(f"      - {file_type}: {file_name}")
                
                # Show file sizes
                print("   📋 File Details:")
                for file_type, file_path in generated_files.items():
                    try:
                        size_bytes = os.path.getsize(file_path)
                        if size_bytes < 1024:
                            size_str = f"{size_bytes} bytes"
                        elif size_bytes < 1024 * 1024:
                            size_str = f"{size_bytes/1024:.1f} KB"
                        else:
                            size_str = f"{size_bytes/(1024*1024):.1f} MB"
                        print(f"      - {os.path.basename(file_path)}: {size_str}")
                    except OSError:
                        print(f"      - {os.path.basename(file_path)}: Size unknown")
        
        except ImportError as e:
            print(f"❌ Phase 4 failed: {e}")
            print("💡 Install pandas to enable output generation: pip install pandas")
            phase4_duration = 0
        except Exception as e:
            print(f"❌ Phase 4 failed with error: {e}")
            phase4_duration = 0
        
        # Save final combined results for all phases
        final_results = {
            "phase1": results,
            "phase2": {
                "scored_queries_count": len(scored_queries),
                "execution_time": phase2_duration,
                "top_5_queries": scored_queries[:5] if scored_queries else []
            },
            "phase3": {
                "scored_dashboards_count": len(scored_dashboards),
                "execution_time": phase3_duration,
                "top_5_dashboards": scored_dashboards[:5] if scored_dashboards else []
            },
            "phase4": {
                "execution_time": phase4_duration,
                "generated_files": generated_files if 'generated_files' in locals() else {}
            }
        }
        
        with open('complete_golden_analysis_results.json', 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, default=str)
        print("💾 Complete analysis results saved to complete_golden_analysis_results.json")
        
        total_time = (datetime.now() - start_time).total_seconds()
        print("\n" + "="*70)
        print("🎉 GOLDEN ASSET RANKING SYSTEM COMPLETE! 🎉")
        print(f"⏱️  Total execution time: {total_time:.2f} seconds")
        print("📊 Analysis Summary:")
        print(f"   • {len(scored_queries)} queries scored and ranked")
        print(f"   • {len(scored_dashboards)} dashboards scored and ranked") 
        if 'generated_files' in locals() and generated_files:
            print(f"   • {len(generated_files)} output files generated")
        print("="*70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
