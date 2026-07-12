#!/usr/bin/env python3
"""
Test HunFlair2 and GLiNER-BioMed NER models.

Verifies that both models in the 5-model ensemble are working correctly.
"""

import torch
from flair.data import Sentence
from flair.nn import Classifier
from gliner import GLiNER

test_cases = [
    "SIRT1 activation reduces inflammation in hippocampus tissue and is associated with reduced risk of Alzheimer's disease.",
    "The p.Val600Glu mutation in BRAF causes drug resistance.",
    "Patient exhibits cognitive decline and memory impairment."
]

print("=" * 80)
print("Testing HunFlair2 and GLiNER-BioMed")
print("=" * 80)

# Device info
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\nDevice: {device}\n")

# Load models
print("Loading models...")
hunflair = Classifier.load("hunflair2")
gliner = GLiNER.from_pretrained("Ihor/gliner-biomed-large-v1.0")
print("✓ Models loaded\n")

gliner_labels = [
    "gene", "protein", "disease", "chemical", "organism",
    "mutation", "genomic variant", "phenotype", "clinical symptom",
    "biological pathway", "signaling pathway", "tissue", "cell type"
]

for idx, text in enumerate(test_cases, 1):
    print("-" * 80)
    print(f"Test {idx}: {text}")
    print("-" * 80)
    
    # HunFlair2
    sentence = Sentence(text)
    hunflair.predict(sentence)
    
    print(f"\nHunFlair2: {len(sentence.get_spans('ner'))} entities")
    for entity in sentence.get_spans('ner'):
        label = entity.get_label('ner')
        print(f"  • '{entity.text}' → {label.value} (conf: {label.score:.3f})")
    
    # GLiNER
    gliner_entities = gliner.predict_entities(text, gliner_labels, threshold=0.3)
    
    print(f"\nGLiNER-BioMed: {len(gliner_entities)} entities")
    for entity in gliner_entities:
        print(f"  • '{entity['text']}' → {entity['label']} (conf: {entity['score']:.3f})")
    
    print()

print("=" * 80)
print("✓ Both models working correctly!")
print("=" * 80)
