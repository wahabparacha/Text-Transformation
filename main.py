# main.py

import pandas as pd
from answer_start_generator import transform_question

def process_questions_from_file(input_file, output_file):
    try:
        df = pd.read_excel(input_file)
        # Convert all questions to strings to avoid TypeError
        df['Question'] = df['Question'].astype(str)
        # Apply the transformation function to each question
        df['Transformed'] = df['Question'].apply(transform_question)
        # Save the transformed questions back to a new Excel file
        df.to_excel(output_file, index=False)
        print("Transformation complete. Transformed questions saved to", output_file)
    except Exception as e:
        print("An error occurred:", e)

def process_single_question(question):
    return transform_question(question)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Transform questions either from a file or a single input")
    parser.add_argument("--file", type=str, help="Input file containing questions")
    parser.add_argument("--output", type=str, help="Output file for transformed questions")
    parser.add_argument("--question", type=str, help="A single question to transform")

    args = parser.parse_args()

    if args.file and args.output:
        process_questions_from_file(args.file, args.output)
    elif args.question:
        transformed_question = process_single_question(args.question)
        print("Transformed Question:", transformed_question)
    else:
        print("Please provide either an input file and output file or a single question to transform.")
