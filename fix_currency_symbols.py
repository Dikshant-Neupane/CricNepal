"""Fix currency symbols in documentation files."""
import glob
import os

# Replace Indian Rupee (₹) with Nepali Rupee (₨)
for filepath in glob.glob('docs/*.md'):
    print(f"Processing {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count replacements
    count = content.count('₹')
    if count > 0:
        # Replace all instances
        new_content = content.replace('₹', '₨')
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✓ Replaced {count} instances of ₹ with ₨")
    else:
        print(f"  - No changes needed")

print("\n✅ Currency symbol fix complete!")
