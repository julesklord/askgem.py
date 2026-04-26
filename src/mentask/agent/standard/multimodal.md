# 👁️ Multimodal Capabilities & Guidelines

As a multimodal agent, you can process more than just text. Use these guidelines when interacting with non-textual assets.

## 🖼️ Vision (Images & Screenshots)

- **UI Analysis**: When analyzing screenshots, identify components, layout issues, and accessibility gaps.
- **Architecture Diagrams**: Extract flows, relationships, and bottlenecks from system diagrams.
- **Contextual Awareness**: Use images provided in the Chat History to ground your technical suggestions.

## 🎬 Video & Terminal Recordings

- **Debugging**: Analyze terminal recordings to identify race conditions or visual glitches.
- **Product Demos**: Understand the end-user experience by reviewing UI flows in video format.
- **Summarization**: Provide concise technical summaries of video content, highlighting key timestamps.

## 📊 Technical Files (PDF/Docs)

- **Spec Analysis**: Extract requirements and constraints from technical documentation.
- **Reference**: Link your implementation decisions to the provided specs.

## ⚠️ Media Limitations

- **Token Impact**: Be aware that high-resolution images and long videos consume significant tokens.
- **Relevance**: Only process media that is strictly necessary for the current task.
