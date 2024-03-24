import time


def merge_wordlists(file_path1, file_path2, output_file_path):
    start_time = time.time()

    # Load words from the first file
    with open(file_path1, 'r', encoding='utf-8') as file1:
        words1 = file1.read().splitlines()

    # Load words from the second file
    with open(file_path2, 'r', encoding='utf-8') as file2:
        words2 = file2.read().splitlines()

    # Combine the lists and remove duplicates
    all_words = list(set(words1 + words2))

    # Save the combined list to a new file
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\n'.join(all_words))

    end_time = time.time()

    # Print calculations
    print(f"Document 1 words: {len(words1)}")
    print(f"Document 2 words: {len(words2)}")
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print(f"Combined file words (unique): {len(all_words)}")


# Example usage
merge_wordlists('../wordlist/Ar_dictionary_stemmed.txt', '../wordlist/ar-wordlist-stemmed.txt', 'combined_wordlist.txt')