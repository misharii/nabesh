from farasa.stemmer import FarasaStemmer
import traceback


class ArabicRootFinder:
    def __init__(self):
        # Initialize Farasa stemmer; this might require handling Java dependencies
        self.stemmer = FarasaStemmer(interactive=True)

    def stem_and_deduplicate_wordlist(self, input_file_path, output_file_path):
        try:
            with open(input_file_path, 'r', encoding='utf-8') as input_file:
                words = input_file.readlines()

            # Use a set to store stemmed words for automatic deduplication
            stemmed_words_set = set()

            for word in words:
                word = word.strip()
                if word:  # Check if the line is not empty
                    stemmed_word = self.stemmer.stem(word)
                    stemmed_words_set.add(stemmed_word)

            # Writing the deduplicated, stemmed words to output file
            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                for word in sorted(stemmed_words_set):
                    output_file.write(word + '\n')

            print("Wordlist stemmed and deduplicated successfully.")

        except Exception as e:
            print("An error occurred while processing the wordlist.")
            traceback.print_exc()


if __name__ == "__main__":
    input_file_path = '/Users/mohammedalsowelim/Downloads/for_nbsh/vocabs/arabert_vocab.txt'  # Your original wordlist file path
    output_file_path = '/Users/mohammedalsowelim/Downloads/for_nbsh/vocabs/arabert_vocabAfterStem.txt'  # File path to save the stemmed and deduplicated wordlist
    root_finder = ArabicRootFinder()
    root_finder.stem_and_deduplicate_wordlist(input_file_path, output_file_path)