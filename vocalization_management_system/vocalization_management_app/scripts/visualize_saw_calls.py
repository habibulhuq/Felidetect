import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Add the project root to the path so we can import the app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))  
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vocalization_management_system.settings')

import django
django.setup()

# Now we can import from the app
from vocalization_management_system.vocalization_management_app.visualization_tools import (
    load_and_merge_data,
    create_timeline_visualization,
    create_frequency_magnitude_plot,
    create_heatmap,
    create_summary_statistics,
    export_visualizations,
    load_data_from_database,
    visualize_database_data
)


def main():
    """Main function to run the visualization script"""
    print("\n===== Big Cat Vocalization Analysis Tool =====\n")
    print("This tool helps you visualize and analyze saw call data from big cat vocalizations.")
    print("It can work with Excel files or directly with the database.\n")
    
    # Ask for the visualization mode
    print("Select a visualization mode:")
    print("1. Visualize data from Excel files (merge existing and new data)")
    print("2. Visualize data directly from the database")
    mode = input("Enter your choice (1 or 2): ")
    
    if mode == "1":
        # Excel file mode
        existing_excel = input("\nEnter the path to the existing Excel file: ")
        new_excel = input("Enter the path to the new Excel file: ")
        
        # Validate file paths
        if not os.path.exists(existing_excel):
            print(f"Error: File not found: {existing_excel}")
            return
        
        if not os.path.exists(new_excel):
            print(f"Error: File not found: {new_excel}")
            return
        
        # Ask for output directory
        output_dir = input("\nEnter the output directory for visualizations: ")
        os.makedirs(output_dir, exist_ok=True)
        
        print("\nProcessing data and generating visualizations...")
        success = export_visualizations(existing_excel, new_excel, output_dir)
        
        if success:
            print(f"\nSuccess! Visualizations have been saved to: {output_dir}")
            print("The following files were created:")
            print("  - timeline_visualization_*.png - Shows call timestamps with frequency and magnitude")
            print("  - frequency_magnitude_plot_*.png - Shows the relationship between frequency and magnitude")
            print("  - heatmap_*.png - Shows the density of calls over time and frequency")
            print("  - merged_data_*.xlsx - Contains the merged data and summary statistics")
        else:
            print("\nError: Failed to generate visualizations.")
    
    elif mode == "2":
        # Database mode
        days_limit = input("\nEnter the number of days to look back (default: 30): ")
        days_limit = int(days_limit) if days_limit.strip() else 30
        
        # Ask if user wants to save visualizations
        save_option = input("\nDo you want to save the visualizations? (y/n): ").lower()
        
        if save_option == 'y':
            output_dir = input("Enter the output directory for visualizations: ")
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = None
        
        print(f"\nLoading data from the database (last {days_limit} days) and generating visualizations...")
        success = visualize_database_data(output_dir, days_limit)
        
        if success:
            if output_dir:
                print(f"\nSuccess! Visualizations have been saved to: {output_dir}")
            else:
                print("\nSuccess! Visualizations have been displayed.")
        else:
            print("\nError: Failed to generate visualizations.")
    
    else:
        print("\nInvalid choice. Please run the script again and select 1 or 2.")


if __name__ == "__main__":
    main()
