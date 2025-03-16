# AI-Enhanced Mesh Detection for Injury Visualization

This system uses AI to improve the accuracy of mapping between body parts mentioned in medical reports and actual mesh names in 3D models. It significantly enhances the ability to correctly identify and highlight injuries on the 3D model.

## Features

- **AI-Powered Matching**: Uses Mistral AI or Google Gemini to semantically match body parts to mesh names
- **Fallback Mechanisms**: Multiple layers of fallback for when AI is unavailable
- **Learning Capability**: Improves over time by learning from successful matches
- **Anatomical Knowledge Base**: Includes a comprehensive database of anatomical terms and relationships
- **Side Detection**: Intelligently handles left/right side specifications
- **Robust Error Handling**: Gracefully handles errors and provides detailed logging

## Setup

### Prerequisites

- Python 3.8+
- Required packages: `requests`, `numpy`, `scikit-learn`
- Optional: Mistral AI or Google Gemini API key for enhanced accuracy

### Installation

1. Ensure all files are in the `python_backend` directory:
   - `anatomical_ai_service.py`
   - `anatomical_knowledge.json`
   - `test_ai_mesh_detection.py`
   - `test_ai_mesh_detection_with_gemini.py`

2. Install required packages:
   ```bash
   # For basic functionality
   pip install -r ai_mesh_detection_requirements.txt
   
   # For Gemini API support
   pip install -r gemini_requirements.txt
   ```

3. Set up your API key (optional but recommended):
   ```bash
   # For Mistral AI
   export MISTRAL_API_KEY=your_api_key_here
   
   # For Google Gemini
   export GEMINI_API_KEY=your_api_key_here
   ```

## Usage

### In Code

The AI-enhanced mesh detection is automatically integrated into the injury visualization system. When processing injuries, the system will:

1. Try to use AI to find the best matching meshes for each body part
2. Fall back to traditional mapping if AI is unavailable
3. Use multiple fallback strategies to ensure the best possible match

Example with Mistral AI:

```python
from anatomical_ai_service import AnatomicalAIService

# Initialize the service with Mistral AI
service = AnatomicalAIService(
    api_key="your_mistral_api_key",
    api_type="mistral"
)

# Find matching meshes
meshes = ["Mesh1", "Mesh2", "Plantaris muscle.r", "Abductor digiti minimi of foot.r"]
matches = service.find_matching_meshes("foot", meshes, "right")
```

Example with Google Gemini:

```python
from anatomical_ai_service import AnatomicalAIService

# Initialize the service with Google Gemini
service = AnatomicalAIService(
    api_key="your_gemini_api_key",
    api_type="gemini"
)

# Find matching meshes
meshes = ["Mesh1", "Mesh2", "Plantaris muscle.r", "Abductor digiti minimi of foot.r"]
matches = service.find_matching_meshes("foot", meshes, "right")
```

### Testing

You can test the AI-enhanced mesh detection using the provided test scripts:

For Mistral AI:
```bash
python test_ai_mesh_detection.py --api-key your_mistral_api_key --verbose
```

For Google Gemini:
```bash
python test_ai_mesh_detection_with_gemini.py --api-key your_gemini_api_key --verbose
```

You can also set the API key as an environment variable:
```bash
# For Mistral AI
export MISTRAL_API_KEY=your_api_key_here
python test_ai_mesh_detection.py --verbose

# For Google Gemini
export GEMINI_API_KEY=your_api_key_here
python test_ai_mesh_detection_with_gemini.py --verbose
```

## How It Works

1. **Body Part Recognition**:
   - The system first tries to recognize the body part using AI
   - It then maps the body part to standardized names

2. **Mesh Detection**:
   - The system uses AI to find meshes that match the body part
   - It considers synonyms, anatomical relationships, and both Latin and common English terms

3. **Side Filtering**:
   - The system filters meshes based on the specified side (left/right)
   - If no side-specific meshes are found, it tries to find neutral meshes

4. **Learning**:
   - The system learns from successful matches and updates its knowledge base
   - This improves accuracy over time

## Extending the System

### Adding New Anatomical Knowledge

You can extend the anatomical knowledge base by editing the `anatomical_knowledge.json` file:

```json
{
  "synonyms": {
    "new_term": ["synonym1", "synonym2"]
  },
  "relationships": {
    "new_term": ["related_term1", "related_term2"]
  }
}
```

### Customizing AI Behavior

You can customize the AI behavior by modifying the `anatomical_ai_service.py` file:

- Adjust the prompt template in `_ai_based_matching`
- Modify the fallback logic in `_local_fallback_matching`
- Change the learning behavior in `learn_from_correction`

## Troubleshooting

### Common Issues

1. **AI Service Not Available**:
   - Check if you have set the appropriate API key environment variable
   - Ensure you have internet connectivity
   - The system will fall back to local methods

2. **Poor Matching Quality**:
   - Try expanding the anatomical knowledge base
   - Run the test script to identify problematic matches
   - Consider using a more powerful AI model

3. **Performance Issues**:
   - The AI service caches results to improve performance
   - Consider using the local fallback for time-critical applications

## Choosing Between Mistral AI and Google Gemini

Both Mistral AI and Google Gemini provide excellent results for anatomical mesh matching. Here are some considerations:

- **Mistral AI**: Specialized in medical and anatomical knowledge, may provide more accurate results for complex anatomical terms.
- **Google Gemini**: More widely available, excellent general knowledge, and may be more cost-effective.

We recommend testing both to see which works best for your specific use case.

## License

This system is part of the AMS Solution Challenge and is subject to the same licensing terms as the rest of the project. 