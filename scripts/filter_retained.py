import csv
import argparse
from difflib import SequenceMatcher


def normalize(name):
    return [t.strip().lower() for t in name.replace('.', '').split() if t.strip()]


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def is_match(csv_name, retained_name):
    c_tokens = normalize(csv_name)
    r_tokens = normalize(retained_name)
    if not c_tokens or not r_tokens:
        return False
    # exact subset
    if set(r_tokens).issubset(set(c_tokens)) or set(c_tokens).issubset(set(r_tokens)):
        return True
    # small fuzzy match on joined names (higher threshold to avoid false positives)
    if similar(' '.join(c_tokens), ' '.join(r_tokens)) > 0.88:
        return True
    return False


def load_retained(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def filter_file(input_csv, retained_file, out_csv, report_md):
    retained = load_retained(retained_file)
    removed = []
    kept = []
    rows = []
    with open(input_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for r in reader:
            name = r['bowler']
            matched = False
            for rr in retained:
                if is_match(name, rr):
                    matched = True
                    removed.append((name, rr))
                    break
            if not matched:
                kept.append(name)
                rows.append(r)

    # write filtered csv
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    # write report
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write('# Retained Filter Report\n\n')
        f.write('Input: {}\n\n'.format(input_csv))
        f.write('Removed rows (matched to retained):\n\n')
        if removed:
            for c, r in removed:
                f.write('- {}  -> matched retained: {}\n'.format(c, r))
        else:
            f.write('None\n')
        f.write('\nKept rows: {}\n'.format(len(kept)))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--retained', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--report', required=True)
    args = p.parse_args()
    filter_file(args.input, args.retained, args.output, args.report)
