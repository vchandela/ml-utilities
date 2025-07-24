#!/usr/bin/env python3
"""
Master test runner for all Vertex AI Feature Store functions.
Runs tests in the order specified in the Testing Workflow.
"""

import os
import subprocess
import sys

def run_test(test_script):
    """Run a single test script."""
    print(f"\n{'='*60}")
    print(f"Running {test_script}")
    print('='*60)
    
    try:
        # Run the test script
        result = subprocess.run([sys.executable, test_script], 
                              cwd=os.path.dirname(__file__),
                              check=False,
                              capture_output=False)
        
        if result.returncode == 0:
            print(f"\n✅ {test_script} completed successfully")
        else:
            print(f"\n❌ {test_script} failed with return code {result.returncode}")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"\n❌ Error running {test_script}: {e}")
        return False

def main():
    """Run all tests in the Testing Workflow order."""
    print("Vertex AI Feature Store - Test Runner")
    print("="*60)
    
    # Test scripts in Testing Workflow order
    test_scripts = [
        "test_create_feature_group.py",
        "test_get_feature_group.py", 
        "test_list_feature_groups.py",
            "test_create_feature.py",
    "test_list_features.py",
    "test_create_online_store.py",
    "test_get_online_store.py",
    "test_create_feature_view.py",
        "test_sync_feature_view.py",
        "test_fetch_feature_values.py"
    ]
    
    # Check if all test files exist
    missing_files = []
    for script in test_scripts:
        if not os.path.exists(script):
            missing_files.append(script)
    
    if missing_files:
        print(f"❌ Missing test files: {', '.join(missing_files)}")
        return 1
    
    print("Available tests:")
    for i, script in enumerate(test_scripts, 1):
        print(f"  {i}. {script}")
    
    print("\nOptions:")
    print("  - Enter test number (1-9) to run specific test")
    print("  - Enter 'all' to run all tests sequentially")
    print("  - Enter 'quit' to exit")
    
    while True:
        choice = input("\nEnter your choice: ").strip().lower()
        
        if choice == 'quit' or choice == 'q':
            print("Exiting...")
            break
            
        elif choice == 'all':
            print("\nRunning all tests in Testing Workflow order...")
            success_count = 0
            
            for script in test_scripts:
                success = run_test(script)
                if success:
                    success_count += 1
                
                # Ask if user wants to continue after each test
                continue_choice = input(f"\nContinue to next test? (y/n): ").strip().lower()
                if continue_choice == 'n':
                    break
            
            print(f"\n{'='*60}")
            print(f"Testing Summary: {success_count}/{len(test_scripts)} tests completed successfully")
            print('='*60)
            break
            
        elif choice.isdigit():
            test_num = int(choice)
            if 1 <= test_num <= len(test_scripts):
                script = test_scripts[test_num - 1]
                run_test(script)
            else:
                print(f"Invalid test number. Please enter 1-{len(test_scripts)}")
        else:
            print("Invalid choice. Please enter a test number, 'all', or 'quit'")

if __name__ == "__main__":
    main() 