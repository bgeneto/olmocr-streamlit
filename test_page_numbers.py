#!/usr/bin/env python3
"""
Simple test to verify page numbers functionality works correctly.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from olmocr.pipeline import build_dolma_document
from olmocr.prompts import PageResponse
from olmocr.pipeline import PageResult
import argparse


def test_page_numbers():
    """Test that page numbers are correctly added when the flag is set"""

    # Create mock page results
    page_results = [
        PageResult(
            s3_path="test.pdf",
            page_num=1,
            response=PageResponse(
                natural_text="This is the content of page 1.",
                primary_language="en",
                is_rotation_valid=True,
                rotation_correction=0,
                is_table=False,
                is_diagram=False,
            ),
            input_tokens=50,
            output_tokens=25,
            is_fallback=False,
        ),
        PageResult(
            s3_path="test.pdf",
            page_num=2,
            response=PageResponse(
                natural_text="This is the content of page 2.",
                primary_language="en",
                is_rotation_valid=True,
                rotation_correction=0,
                is_table=False,
                is_diagram=False,
            ),
            input_tokens=55,
            output_tokens=28,
            is_fallback=False,
        ),
    ]

    # Test WITHOUT page numbers
    args_without = argparse.Namespace()
    args_without.add_page_numbers = False

    doc_without = build_dolma_document("test.pdf", page_results, args_without)
    print("=== WITHOUT page numbers ===")
    print(doc_without["text"])
    print()

    # Test WITH page numbers
    args_with = argparse.Namespace()
    args_with.add_page_numbers = True

    doc_with = build_dolma_document("test.pdf", page_results, args_with)
    print("=== WITH page numbers ===")
    print(doc_with["text"])
    print()

    # Verify page numbers are added correctly
    expected_with_pages = "--- Page 1 ---\n\nThis is the content of page 1.\n--- Page 2 ---\n\nThis is the content of page 2."
    expected_without_pages = "This is the content of page 1.\nThis is the content of page 2."

    if doc_with["text"] == expected_with_pages:
        print("✅ Page numbers test PASSED")
    else:
        print("❌ Page numbers test FAILED")
        print(f"Expected: {repr(expected_with_pages)}")
        print(f"Got: {repr(doc_with['text'])}")

    if doc_without["text"] == expected_without_pages:
        print("✅ Without page numbers test PASSED")
    else:
        print("❌ Without page numbers test FAILED")
        print(f"Expected: {repr(expected_without_pages)}")
        print(f"Got: {repr(doc_without['text'])}")


if __name__ == "__main__":
    test_page_numbers()
