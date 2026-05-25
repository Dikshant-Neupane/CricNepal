import csv
import argparse


def generate(input_csv, out_md, top_n=5):
    rows = []
    with open(input_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                score = float(r.get('composite_score', '9999'))
            except:
                score = 9999
            rows.append((score, r))
    rows.sort(key=lambda x: x[0])
    top = [r for s, r in rows[:top_n]]

    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('# S3 CEO Shortlist (Filtered — Top {})\n\n'.format(top_n))
        f.write('Date: May 25, 2026\n\n')
        for i, r in enumerate(top, 1):
            f.write(f"{i}. {r['bowler']}\n")
            f.write(f"   - PP econ: {r['pp_econ']} ({r['pp_balls']} balls), Death econ: {r['death_econ']} ({r['death_balls']} balls)\n")
            f.write('   - Draft priority: 1 (High)\n\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--top', type=int, default=5)
    args = parser.parse_args()
    generate(args.input, args.out, args.top)
