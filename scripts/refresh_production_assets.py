import shutil
import os
from pathlib import Path

def main():
    print("Refreshing Production Assets...")
    
    # Define paths
    source_dir = Path("data/normalized")
    dest_dir = Path("data/production_assets/parquet")
    
    # Ensure destination exists
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_copy = [
        "matches_normalized.parquet",
        "ball_by_ball_normalized.parquet"
    ]
    
    for filename in files_to_copy:
        src = source_dir / filename
        dst = dest_dir / filename
        
        if src.exists():
            shutil.copy2(src, dst)
            print(f"Copied {filename} to production assets.")
        else:
            print(f"Warning: Source {src} not found!")

if __name__ == '__main__':
    main()
