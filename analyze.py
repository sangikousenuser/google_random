"""Analyze a recorded sample; partial runs are explicitly marked."""
import argparse
import csv
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import chisquare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path', type=Path)
    parser.add_argument('--expected', type=int, default=10000)
    args = parser.parse_args()
    with args.csv_path.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError('No samples collected')
    values = [int(row['value']) for row in rows]
    if any(not 1 <= v <= 41 for v in values):
        raise ValueError('Values outside 1..41')
    if [int(r['trial']) for r in rows] != list(range(1, len(rows) + 1)):
        raise ValueError('Trial indices are missing or duplicated')
    counts = Counter(values)
    n = len(values)
    frequencies = [counts[i] for i in range(1, 42)]
    stat, p = chisquare(frequencies)
    target = args.csv_path.parent
    with (target / 'frequencies.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['value', 'count', 'percent', 'expected_count'])
        for i, count in enumerate(frequencies, 1):
            writer.writerow([i, count, 100 * count / n, n / 41])
    result = (f'Samples: {n} / {args.expected} '
              f'({"COMPLETE" if n == args.expected else "PARTIAL"})\n'
              f'Uniform expected count per value: {n / 41:.3f}\n'
              f'Minimum / maximum observed counts: {min(frequencies)} / {max(frequencies)}\n')
    if n / 41 >= 5:
        result += f'Chi-square: {stat:.6f}; df=40; p={p:.6g}\n'
        result += ('Uniformity rejected at the 5% level.\n' if p < .05 else
                   'Uniformity not rejected at the 5% level; this does not prove fairness.\n')
    else:
        result += 'Too few observations for the chi-square approximation.\n'
    result += 'This frequency test does not establish independence or predict future outputs.\n'
    (target / 'summary.txt').write_text(result)
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.bar(range(1, 42), frequencies)
    ax.axhline(n / 41, color='red', linestyle='--', label='Uniform expected count')
    ax.set(xlabel='Value', ylabel='Count', title=f'Google random widget: {n} recorded outputs')
    ax.set_xticks(range(1, 42))
    ax.legend()
    fig.tight_layout()
    fig.savefig(target / 'distribution.png', dpi=160)
    plt.close(fig)
    print(result)


if __name__ == '__main__':
    main()
