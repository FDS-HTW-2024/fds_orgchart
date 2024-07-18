import argparse
from collections import defaultdict
from concurrent.futures import as_completed, ThreadPoolExecutor
from queue import Queue

from organigram_extract.data import Drawing
from organigram_extract.extract import extract_document
import organigram_extract.pdf as pdf
from organigram_extract.text_pipeline import TextPipeline

def run():
    parser = argparse.ArgumentParser(prog='Organigramm Extract')

    parser.add_argument('filename', help='source file for extraction')
    parser.add_argument('-o', '--output_file', help='output file to write the extracted content')
    
    args = parser.parse_args()

    worker_threads = 8

    with ThreadPoolExecutor(max_workers=worker_threads) as executor:
        text_tasks = Queue(1)
        text_results = Queue(1)

        # Process all text in a separate thread
        #
        # The text pipeline components are created once to avoid using too
        # much memory accidentally.
        text_processing = executor.submit(process_text, text_tasks, text_results)

        tasks = [executor.submit(process_drawing, id, drawing, text_tasks, text_results)
                 for (id, drawing) in enumerate(pdf.open(args.filename))]

        for future in as_completed(tasks):
            (document, result) = future.result()
            for (_, text) in result:
                print("============")
                print(text)
            

        # Shutdown text processing thread
        text_tasks.put(None)
        text_processing.result()

def process_drawing(
        id: int,
        drawing: Drawing,
        text_tasks: Queue,
        text_results: Queue):
    print("PROCESS DRAWING...")
    document = extract_document(drawing)
    count = 0
    task_count = len(document.text_contents)

    for (rect, text) in document.text_contents.items():
        count += 1
        is_finished = count == task_count
        text_tasks.put((text, (id, rect, is_finished)))

    while True:
        (result_id, results) = text_results.get()

        if result_id == id:
            text_results.task_done()
            return (document, results)

def process_text(text_tasks: Queue, text_results: Queue):
    print("PROCESS TEXT...")
    pipeline = TextPipeline()
    results = defaultdict(list)

    for (text, (id, rect, is_finished)) in iter(text_tasks.get, None):
        result = pipeline.process(text)
        results[id].append((rect, result))

        if is_finished:
            text_results.put((id, results[id]))
            del results[id]
