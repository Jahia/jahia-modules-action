"""Build one prompt per batch of tickets.

Usage: build-prompts.py <template-path> <rubric-path> <log-dir> <batch-size> <key>...

Each batch is one agent run, so a long selection never fills one context. Writes
<log-dir>/batch-<n>.prompt.md for each batch, and prints the number of batches.
"""
import os
import sys


def batches(keys, size):
    return [keys[i:i + size] for i in range(0, len(keys), size)]


def main():
    template_path, rubric_path, log_dir, size = sys.argv[1:5]
    keys = sys.argv[5:]
    factors_dir = os.path.join(log_dir, 'factors')
    os.makedirs(factors_dir, exist_ok=True)
    with open(template_path, encoding='utf-8') as fh:
        template = fh.read()
    groups = batches(keys, max(1, int(size)))
    for n, group in enumerate(groups, 1):
        listing = '\n'.join(
            f'- `{os.path.join(log_dir, "tickets", key + ".json")}` → `{os.path.join(factors_dir, key + ".json")}`'
            for key in group)
        prompt = (template
                  .replace('__RUBRIC__', rubric_path)
                  .replace('__COUNT__', str(len(group)))
                  .replace('__TICKETS__', listing))
        with open(os.path.join(log_dir, f'batch-{n}.prompt.md'), 'w', encoding='utf-8') as fh:
            fh.write(prompt)
    print(len(groups))


if __name__ == '__main__':
    main()
