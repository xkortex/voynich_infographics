#!/usr/bin/env python3
"""Full-resolution, resumable OCR of a scanned PDF on macOS.

Requires: brew install poppler tesseract tesseract-lang
Example:
  python3 ocr_fullres_mac.py CCSL_160_Corpus_orationum_A-C.pdf --dpi 400 --workers 2
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import re
import subprocess
import tempfile


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def pages_in_pdf(pdf):
    info = subprocess.check_output(['pdfinfo', str(pdf)], text=True)
    m = re.search(r'^Pages:\s*(\d+)', info, re.MULTILINE)
    if not m:
        raise RuntimeError('Cannot find PDF page count with pdfinfo')
    return int(m.group(1))


def ocr_page(page, pdf, pages_dir, dpi, lang, psm, force):
    out = pages_dir / f'{page:04d}.txt'
    if out.exists() and not force:
        return page, 'cached'
    with tempfile.TemporaryDirectory(prefix=f'ocr_{page:04d}_') as tmp:
        img = Path(tmp) / 'page.png'
        run('pdftoppm', '-f', str(page), '-l', str(page), '-singlefile',
            '-r', str(dpi), '-gray', '-png', str(pdf), str(img.with_suffix('')),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        env = os.environ.copy()
        env['OMP_THREAD_LIMIT'] = '1'
        result = subprocess.run(
            ['tesseract', str(img), 'stdout', '-l', lang,
             '--oem', '1', '--psm', str(psm)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=env)
        pending = out.with_suffix('.txt.tmp')
        pending.write_text(result.stdout, encoding='utf-8')
        pending.replace(out)
    return page, 'done'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pdf', type=Path)
    p.add_argument('--dpi', type=int, default=400)
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--lang', default='lat+fra+eng',
                   help='Tesseract languages (default: lat+fra+eng)')
    p.add_argument('--psm', type=int, default=3,
                   help='Tesseract page segmentation mode (default: 3)')
    p.add_argument('--output', type=Path, default=None)
    p.add_argument('--workdir', type=Path, default=None)
    p.add_argument('--force', action='store_true', help='Redo cached pages')
    args = p.parse_args()
    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file():
        p.error(f'PDF does not exist: {pdf}')
    if args.workers < 1 or args.dpi < 72:
        p.error('Workers must be >=1 and DPI >=72')
    out = args.output or pdf.with_name(pdf.stem + '_fullres_ocr.txt')
    out = out.expanduser().resolve()
    pages_dir = (args.workdir or pdf.with_name(pdf.stem + '_ocr_pages')).expanduser().resolve()
    pages_dir.mkdir(parents=True, exist_ok=True)
    count = pages_in_pdf(pdf)
    print(f'{count} pages | {args.dpi} DPI | languages {args.lang} | {args.workers} workers', flush=True)
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(ocr_page, i, pdf, pages_dir, args.dpi,
                               args.lang, args.psm, args.force): i
                   for i in range(1, count + 1)}
        for n, future in enumerate(as_completed(futures), start=1):
            i = futures[future]
            try:
                _, status = future.result()
                print(f'[{n}/{count}] page {i}: {status}', flush=True)
            except Exception as e:
                errors.append(i)
                print(f'[{n}/{count}] page {i}: ERROR: {e}', flush=True)
    if errors:
        raise SystemExit(f'Failed pages: {sorted(errors)}. Re-run to retry; cached pages are kept.')
    with out.open('w', encoding='utf-8') as f:
        for i in range(1, count + 1):
            f.write(f'\n\n===== PDF PAGE {i} =====\n\n')
            f.write((pages_dir / f'{i:04d}.txt').read_text(encoding='utf-8'))
    print(f'Wrote {out}', flush=True)


if __name__ == '__main__':
    main()
