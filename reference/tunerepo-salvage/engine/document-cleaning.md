# Document Cleaning

The Document Cleaning feature in Universal Document Processor (UDP) prepares raw documents for effective use in machine learning pipelines by removing noise, normalizing content, and enhancing structure.

## Overview

Raw documents often contain elements that can negatively impact machine learning model training, such as:
- Irrelevant boilerplate text
- Duplicate content
- Formatting artifacts
- Header/footer noise
- Inconsistent spacing and formatting
- Special characters and encoding issues

The Document Cleaning module automatically identifies and addresses these issues to produce clean, consistent, and high-quality content.

## Key Features

### Noise Removal

- **Header and Footer Detection**: Automatically identifies and removes repetitive headers, footers, and page numbers
- **Watermark Removal**: Detects and eliminates watermark text that repeats across pages
- **Advertisement Filtering**: Identifies and removes promotional content
- **Boilerplate Elimination**: Removes standard legal disclaimers, copyright notices, and other boilerplate text
- **Citation/Reference Cleaning**: Standardizes or optionally removes citations and references

### Structure Detection

- **Document Hierarchy Analysis**: Identifies document structure (titles, headings, paragraphs, lists)
- **Table Extraction**: Detects tables and converts them to structured formats
- **Figure and Chart Recognition**: Identifies figures and extracts captions
- **List Normalization**: Standardizes bulleted and numbered lists
- **Section Boundary Identification**: Detects logical section boundaries

### Duplicate Detection

- **Cross-Document Deduplication**: Identifies and removes duplicate documents from a corpus
- **Intra-Document Deduplication**: Detects and eliminates redundant content within a document
- **Near-Duplicate Detection**: Identifies content with minor variations
- **Reference Deduplication**: Merges multiple references to the same source
- **Sliding Window Similarity**: Detects localized duplication within larger documents

### Content Normalization

- **Character Encoding Standardization**: Converts to consistent UTF-8 encoding
- **Whitespace Normalization**: Standardizes spacing between paragraphs, sentences, and words
- **Character Replacement**: Substitutes special characters, ligatures, and symbols with standard forms
- **Number and Date Standardization**: Converts various number and date formats to consistent patterns
- **Language Normalization**: Handles multilingual content and standardizes to consistent language patterns

## Configuration Options

### Cleaning Levels

UDP offers several preconfigured cleaning levels:

| Level | Description | Use Case |
|-------|-------------|----------|
| `minimal` | Basic cleaning with minimal content alteration | When preserving original text is critical |
| `standard` | Balanced cleaning for most documents | General document processing |
| `aggressive` | Thorough cleaning that may alter content significantly | When clean training data is the priority |
| `custom` | User-defined cleaning with specific options | For specialized requirements |

### Cleaning Parameters

Fine-tune document cleaning with these parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `remove_headers_footers` | boolean | `true` | Remove page headers and footers |
| `remove_watermarks` | boolean | `true` | Remove watermark text |
| `normalize_whitespace` | boolean | `true` | Standardize spacing throughout document |
| `standardize_quotes` | boolean | `true` | Convert various quote styles to standard quotes |
| `standardize_hyphens` | boolean | `true` | Normalize different hyphen and dash characters |
| `fix_encoding` | boolean | `true` | Correct character encoding issues |
| `remove_urls` | boolean | `false` | Remove URLs and web references |
| `remove_email_addresses` | boolean | `false` | Remove email addresses |
| `remove_citations` | boolean | `false` | Remove in-text citations |
| `remove_references` | boolean | `false` | Remove reference sections |
| `minimum_line_length` | integer | `10` | Minimum character length for a line to be retained |
| `minimum_paragraph_length` | integer | `30` | Minimum character length for a paragraph to be retained |
| `deduplication_threshold` | float | `0.85` | Similarity threshold for duplicate detection (0.0-1.0) |
| `language` | string | `auto` | Document language (or 'auto' for detection) |

## Usage Examples

### Basic Cleaning

```python
from toolrepo import UDP

udp = UDP()

# Using standard cleaning settings
result = udp.process(
    content="Your document content here...",
    cleaning_level="standard"
)

# Print cleaned content
print(result.cleaned_content)
```

### Custom Cleaning Configuration

```python
from toolrepo import UDP

udp = UDP()

# Using custom cleaning settings
result = udp.process(
    content="Your document content here...",
    cleaning_level="custom",
    cleaning_options={
        "remove_headers_footers": True,
        "remove_watermarks": True,
        "normalize_whitespace": True,
        "standardize_quotes": True,
        "remove_citations": False,
        "remove_references": False,
        "minimum_line_length": 5,
        "deduplication_threshold": 0.9
    }
)

# Print cleaned content
print(result.cleaned_content)
```

### API Usage

```bash
curl -X POST https://api.toolrepo.ai/udp/v1/process \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your document content here...",
    "content_type": "text/plain",
    "cleaning_level": "standard"
  }'
```

### Advanced Configuration

```python
from toolrepo import UDP

udp = UDP()

# Advanced cleaning with specialized settings
result = udp.process(
    content="Your document content here...",
    content_type="text/plain",
    cleaning_level="custom",
    cleaning_options={
        "remove_headers_footers": True,
        "remove_watermarks": True,
        "normalize_whitespace": True,
        "standardize_quotes": True,
        "standardize_hyphens": True,
        "fix_encoding": True,
        "remove_urls": False,
        "remove_email_addresses": True,
        "remove_citations": False,
        "remove_references": False,
        "minimum_line_length": 5,
        "minimum_paragraph_length": 20,
        "deduplication_threshold": 0.9,
        "language": "en"
    },
    custom_patterns={
        "remove": [
            r"Copyright © 20\d\d",
            r"All rights reserved\.",
            r"Page \d+ of \d+"
        ],
        "replace": [
            {"pattern": r"Fig\. (\d+)", "replacement": "Figure $1"},
            {"pattern": r"Table (\d+)", "replacement": "Table $1"}
        ]
    }
)
```

## Special Document Types

### PDFs

When processing PDFs, Document Cleaning includes additional specialized features:

- **Column Detection**: Identifies and correctly orders multi-column layouts
- **Text Flow Reconstruction**: Rebuilds proper paragraph flow often broken in PDF extraction
- **Header/Footer Boundary Detection**: Uses layout analysis to identify page margins
- **Font Analysis**: Uses font information to help determine document structure
- **Artifact Removal**: Cleans up PDF-specific extraction artifacts

### Web Content

For web-scraped content, additional cleaning options are available:

- **HTML Tag Removal**: Strips all HTML/XML tags while preserving content
- **Navigation Removal**: Eliminates navigation bars, menus, and sidebars
- **Comment Removal**: Strips user comments and discussion sections
- **Ad Content Filtering**: Removes advertisements and promotional content
- **Article Extraction**: Focuses on the main content of a web page

### Academic Papers

Special processing for academic and scientific papers:

- **Abstract Extraction**: Identifies and preserves abstract sections
- **Figure/Table Caption Handling**: Properly processes captions
- **Equation Processing**: Special handling for mathematical equations
- **Citation Normalization**: Standardizes citation formats
- **Section Standardization**: Normalizes common paper sections (Introduction, Methods, Results, etc.)

## Before and After Examples

### Example 1: Academic Paper

**Before Cleaning**:
```
JOURNAL OF ADVANCED RESEARCH
Vol. 15, No. 2                                                                                                                                 Page 42

A Novel Approach to Document Classification
John Smith¹, Sarah Johnson²
¹Department of Computer Science, University of Example
²AI Research Institute, Example Corp.

ABSTRACT
This paper presents a novel approach to document classification using transformer models...
```

**After Cleaning**:
```
A Novel Approach to Document Classification
John Smith, Sarah Johnson

ABSTRACT
This paper presents a novel approach to document classification using transformer models...
```

### Example 2: PDF with Layout Issues

**Before Cleaning**:
```
Introduction                                                                2
Processing large volumes of text data 
has become increasingly important in     This creates significant 
the field of natural language            challenges for downstream
processing.                              tasks such as classification
                                         and summarization.
```

**After Cleaning**:
```
Introduction

Processing large volumes of text data has become increasingly important in the field of natural language processing. This creates significant challenges for downstream tasks such as classification and summarization.
```

## Performance Considerations

- **Processing Time**: Document cleaning typically adds 10-30% to overall processing time
- **Memory Usage**: Complex cleaning operations may require additional memory
- **Language Support**: Best results are achieved for well-supported languages (English, Spanish, French, German, etc.)
- **Document Size**: Very large documents may require batch processing

## Recommendations

1. **Start with Standard Cleaning**: Begin with the `standard` cleaning level and adjust as needed
2. **Review Cleaned Output**: Periodically review cleaned documents to ensure quality
3. **Customize for Document Types**: Use specialized settings for different document sources
4. **Balance Cleaning vs. Content Preservation**: More aggressive cleaning may remove valuable content
5. **Use Document-Specific Options**: Enable document-type specific options when appropriate

## Integration with Other Features

Document Cleaning works seamlessly with other UDP features:

- **Chunking Strategies**: Cleaned content improves chunking quality
- **OCR Post-Processing**: Applied after OCR to correct recognition artifacts
- **Metadata Extraction**: Helps identify document metadata more accurately
- **Entity Recognition**: Improves entity extraction quality

## Limitations

- **Language Dependence**: Best results for well-supported languages
- **Context Preservation**: Aggressive cleaning may remove contextual information
- **Domain-Specific Content**: May require custom rules for specialized domains
- **Table/Figure Processing**: Complex tables or figures may not be perfectly processed

## Related Features

- [Document Ingestion](/tools/udp/features/document-ingestion)
- [Chunking Strategies](/tools/udp/features/chunking-strategies)
- [Data Transformation](/tools/udp/features/data-transformation)

## Further Reading

- [Natural Language Processing Best Practices](https://example.com/nlp-best-practices)
- [Text Preprocessing for Machine Learning](https://example.com/text-preprocessing)
- [Document Structure Analysis](https://example.com/document-structure)
