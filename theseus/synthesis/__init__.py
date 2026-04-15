"""
theseus/synthesis — Clean-room source synthesis from behavioral specs.

Given a compiled .zspec.json behavioral specification, the synthesis layer:
  1. Prompts an LLM to write a clean-room implementation
  2. Builds the synthesized code (Python / C / JavaScript)
  3. Subjects it to the same verify_behavior.py harness
  4. Iterates on failures up to max_iterations
  5. Annotates the .zspec.zsdl source with the outcome

Public surface:
    from theseus.synthesis.runner import SynthesisRunner, SynthesisResult
    from theseus.synthesis.prompt import PromptBuilder
    from theseus.synthesis.build import SynthesisBuildDriver, backend_lang_for_spec
    from theseus.synthesis.annotate import SynthesisAnnotator
    from theseus.synthesis.audit import AuditReportGenerator
"""
