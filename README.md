# Smart Invoice Processing System

A production-ready invoice processing system that combines OCR with multiple AI providers for intelligent document extraction, validation, and analysis.

## What This System Does

Ever needed to extract structured data from invoices but struggled with different formats and quality? This system solves that problem by:

- **Working with multiple AI providers**: Choose between LlamaIndex Cloud, OpenAI GPT, or Tesseract OCR
- **Being smart about failures**: If one provider doesn't work, it automatically tries another
- **Giving you real insights**: Track processing time, success rates, and confidence scores
- **Validating your data**: Independent checks to make sure the numbers actually make sense
- **Letting you choose**: Pick your preferred provider or let the system auto-detect the best option
- **Being actually useful**: Built with real-world scenarios in mind, not just demos

## How It's Built

I designed this with a clean, layered approach to keep things maintainable:

```
┌─────────────────┐
│   UI Layer      │ ← Simple HTML interface + API endpoints
├─────────────────┤
│  Service Layer  │ ← Smart extractors + main processing logic
├─────────────────┤
│  Domain Layer   │ ← Invoice models + validation rules
└─────────────────┘
```

### The Important Parts

- **SmartExtractorFactory**: Creates and manages different AI providers
- **InvoiceExtractor**: Base class that all providers implement
- **InvoiceProcessor**: The main orchestrator that ties everything together
- **MetricsCollector**: Tracks how well each provider is performing
- **Validation Engine**: Makes sure the numbers actually add up correctly

## Project Structure

```text
invoice_mvp/
├── app/
│   ├── core/
│   │   ├── models.py          # Pydantic models for invoices
│   │   └── __init__.py
│   ├── services/
│   │   ├── extractors/        # Different AI providers live here
│   │   │   ├── base.py        # The interface everyone implements
│   │   │   ├── llama_extractor.py    # LlamaIndex Cloud implementation
│   │   │   ├── openai_extractor.py   # OpenAI implementation
│   │   │   └── ocr_extractor.py      # Tesseract OCR implementation
│   │   ├── smart_extractor.py # Factory that manages providers
│   │   ├── metrics.py         # Performance tracking
│   │   ├── orchestrator.py    # Main processing pipeline
│   │   └── validator.py       # Number validation logic
│   ├── api/
│   │   └── routes.py          # FastAPI endpoints
│   ├── ui/
│   │   └── index.html         # Demo interface
│   └── main.py                # FastAPI app entry point
├── tests/
└── README.md
```

## How It Works

Here's what happens when you upload an invoice:

1. **You upload a file** (PDF or image)
2. **Pick your AI provider** or let the system choose the best one
3. **OCR extracts the text** from your document
4. **AI processes the text** and pulls out structured data
5. **If something fails**, it automatically tries another provider
6. **Validation checks** make sure all the numbers add up correctly
7. **Metrics are tracked** so you know how well everything is working
8. **You get back clean JSON** with validation results

## Supported AI Providers

### 🦙 LlamaIndex Cloud (My Top Pick)
This is usually the best option because:
- It understands document layouts (not just text)
- Processes the original file (PDF/image) directly
- Has built-in OCR optimized for invoices
- Gives confidence scores for extracted data

**Setup**: Just set `LLAMA_API_KEY` environment variable

### 🤖 OpenAI GPT
Great for text-heavy invoices when you have good OCR:
- Works with OCR text only
- Excellent at understanding context
- Flexible parsing capabilities

**Setup**: Set `OPENAI_API_KEY` environment variable

### 📄 Tesseract OCR
The reliable fallback option:
- Works with any PDF/image file
- Uses pattern matching and regex
- Always available as a backup

**Setup**: Install Tesseract OCR on your system

## API Endpoints

### Process an Invoice
```http
POST /api/invoices/process?provider={provider}
Content-Type: multipart/form-data

file: [Your PDF or image file]
```

**Provider options**: 
- `llama` - LlamaIndex Cloud
- `openai` - OpenAI GPT  
- `ocr` - Tesseract OCR
- Leave empty for auto-detection

### See Available Providers
```http
GET /api/providers
```
Tells you which providers are available and which one I recommend.

### Check Performance
```http
GET /api/metrics
```
Shows you how each provider is performing - success rates, processing times, etc.

## What You Get Back

Here's a real example of the JSON response:

```json
{
  "invoice": {
    "provider": {
      "name": "ANDREA CECILIA PORTELA GALLO",
      "rut": "21 705833 0019",
      "address": "Ruta 5 S/N - Durazno"
    },
    "buyer": {
      "name": "UNFPA",
      "rut": "",
      "address": "Dr. Leis Pierar 1992",
      "type": "C.FINAL CRÉDITO"
    },
    "line_items": [
      {
        "rubro_raw": "01 250 x 2 - O.T. 28685A",
        "quantity": 2,
        "unit_price": 0.0,
        "subtotal": 0.0
      }
    ],
    "totals": {
      "subtotal": 69393.0,
      "iva": 15267.0,
      "iva_rate": 0.0,
      "total": 84660.0
    }
  },
  "validation": {
    "is_valid": true,
    "issues": []
  }
}
```

## Getting Started

### What You Need
- Python 3.8 or newer
- Tesseract OCR (only if you want to use the OCR provider)
- API keys for the AI providers you want to use

### Installation

```bash
git clone <repository>
cd invoice_mvp
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux  
source .venv/bin/activate

pip install -r requirements.txt
```

### Environment Setup

```bash
# LlamaIndex Cloud (recommended)
export LLAMA_API_KEY="your_llama_api_key"

# OpenAI (optional)
export OPENAI_API_KEY="your_openai_api_key"

# Force a specific provider (optional)
export INVOICE_LLM_PROVIDER="llama"
```

### Run It

```bash
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000` for the demo interface, or `http://127.0.0.1:8000/docs` for the API documentation.

## Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app

# Run a specific test file
pytest tests/test_pipeline.py
```

## Performance Tracking

The system automatically keeps track of:

- **How long each provider takes** to process invoices
- **Success rates** for each provider
- **Confidence scores** when available
- **Error details** for debugging

All this data gets saved to `extraction_metrics.json` and you can also access it via the `/api/metrics` endpoint.

## Configuration

### Provider Priority
The system tries providers in this order:
1. **LlamaIndex Cloud** (if you have an API key)
2. **OpenAI** (if you have an API key)  
3. **Tesseract OCR** (always available as backup)

### Adding Your Own Provider
Want to add a new AI provider? Here's how:

1. Create a new class that implements `InvoiceExtractor`
2. Add it to the `SmartExtractorFactory`
3. Set up any environment variables it needs
4. Update the UI selector options

## Deployment

### Docker
```bash
docker build -t invoice-processor .
docker run -p 8000:8000 invoice-processor
```

### Environment Variables for Production
```bash
LLAMA_API_KEY=your_production_key
OPENAI_API_KEY=your_production_key
INVOICE_LLM_PROVIDER=llama
```

### Serverless (Vercel, Cloudflare, etc.)
Use `app.main:app` as your ASGI entrypoint. The system is designed to work well in serverless environments - just make sure your environment variables are set properly.

## When Would You Use This?

- **Processing invoices automatically** instead of manual data entry
- **Extracting structured data** from various document formats
- **Making sure financial data is actually correct** with validation
- **Comparing different AI services** to see which works best for your use case
- **Building a reliable system** that won't fail when one provider has issues

## Contributing

I'd love contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for your new functionality
4. Make sure all tests pass (`pytest`)
5. Submit a pull request

## License

This project is under the MIT License - see the LICENSE file for details.

## What's Next?

Some ideas for future improvements:
- **More AI providers**: Azure Document AI, Google Document AI
- **Better validation**: Business rules and industry-specific checks
- **Database integration**: Store processing history and results
- **Batch processing**: Handle multiple invoices at once
- **Webhook support**: Get notified when processing is done
- **Analytics dashboard**: Visual charts and detailed metrics

---

Cecilia Portela +59899361100
