"""Download Sefaria datasets from HuggingFace and print stats."""

from datasets import load_dataset


def main() -> None:
    print("Loading Sefaria Hebrew library...")
    hebrew = load_dataset("Sefaria/hebrew_library", split="train")
    print(f"  Hebrew: {len(hebrew):,} entries")
    print(f"  Columns: {hebrew.column_names}")
    print(f"  Sample:")
    sample = hebrew[0]
    for key, value in sample.items():
        preview = str(value)[:120] if value else "None"
        print(f"    {key}: {preview}")

    print()
    print("Loading Sefaria English library...")
    english = load_dataset("Sefaria/english_library", split="train")
    print(f"  English: {len(english):,} entries")
    print(f"  Columns: {english.column_names}")
    print(f"  Sample:")
    sample = english[0]
    for key, value in sample.items():
        preview = str(value)[:120] if value else "None"
        print(f"    {key}: {preview}")

    print()
    print(f"Total: {len(hebrew) + len(english):,} texts")


if __name__ == "__main__":
    main()
