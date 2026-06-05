import json
from src.chunking import ChunkingStrategyComparator, CustomStructuredChunker

text = open('data/tthc_ly_lich_tu_phap.json', encoding='utf-8').read()
comp = ChunkingStrategyComparator().compare(text)
custom = CustomStructuredChunker().chunk(text)

print(f"Fixed: count={comp['fixed_size']['count']}, avg={comp['fixed_size']['avg_length']:.1f}")
print(f"Sentence: count={comp['by_sentences']['count']}, avg={comp['by_sentences']['avg_length']:.1f}")
print(f"Recursive: count={comp['recursive']['count']}, avg={comp['recursive']['avg_length']:.1f}")
print(f"Custom count: {len(custom)}, avg: {sum(len(c) for c in custom)/len(custom):.1f}")
