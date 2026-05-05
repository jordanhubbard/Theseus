"""
theseus/synthesis/prompt.py

Builds LLM prompts for clean-room source synthesis from ZSDL behavioral specs,
and parses the LLM's file-block response format.

Prompt design principles:
  - System prompt establishes the clean-room constraint once.
  - User prompt gives the full API surface + invariants as the specification.
  - Revision prompt feeds back failed invariant IDs + error messages.
  - Source files are delimited with <file name="..."><content>...</content></file>
    so they can be extracted from free-form LLM responses.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass


_SYSTEM_PROMPT = """\
You are a software engineer implementing a library from its behavioral specification.

Rules:
1. You have NOT seen the original library's source code.
2. Derive your implementation ONLY from public standards, RFCs, and documentation
   listed in the spec's "Public documentation" section.
3. Do NOT import or call the real library you are replacing (e.g. if the spec is
   for "hashlib", your implementation must NOT contain "import hashlib").
4. Your code must be complete and self-contained — no TODO stubs.
5. CRITICAL — output format: your ENTIRE response must consist of ONLY source file
   blocks in the exact format below.  No preamble.  No explanation.  No prose.
   No markdown fences.  Start your response with the first <file ...> tag:
   <file name="FILENAME"><content>
   ...file content...
   </content></file>
""".strip()


@dataclass
class PromptBuilder:
    """Constructs LLM prompts for synthesis and revision."""

    def initial_prompt(self, spec: dict, backend_lang: str) -> tuple[str, str]:
        """
        Build the initial synthesis prompt.

        Returns:
            (system_prompt, user_prompt) tuple.
        """
        return _SYSTEM_PROMPT, _build_initial_user(spec, backend_lang)

    def revision_prompt(
        self,
        spec: dict,
        backend_lang: str,
        previous_source: dict[str, str],
        failed_invariants: list[dict],
        iteration: int,
    ) -> tuple[str, str]:
        """
        Build a revision prompt feeding back failed invariants.

        Args:
            spec: compiled .zspec.json dict.
            backend_lang: synthesis language.
            previous_source: filename → content of the previous attempt.
            failed_invariants: list of {id, message} dicts for failed invariants.
            iteration: current iteration number (1-based).

        Returns:
            (system_prompt, user_prompt) tuple.
        """
        return _SYSTEM_PROMPT, _build_revision_user(
            spec, backend_lang, previous_source, failed_invariants, iteration
        )

    @staticmethod
    def extract_source_files(llm_response: str) -> dict[str, str]:
        """
        Parse source file blocks from the LLM response.

        Primary format (required by system prompt):
            <file name="FILENAME"><content>
            ...file content...
            </content></file>

        Fallback format (markdown fences with filename hint):
            ```python
            # filename.py
            ...
            ```
            or ```python filename.py
            ...
            ```

        Returns:
            dict mapping filename → file content (stripped of leading/trailing
            whitespace within the content block).

        Raises:
            ValueError: if no file blocks are found in the response.
        """
        # Primary: XML file blocks
        xml_pattern = re.compile(
            r'<file\s+name=["\']([^"\']+)["\']\s*>'
            r'\s*<content>(.*?)</content>\s*</file>',
            re.DOTALL,
        )
        matches = xml_pattern.findall(llm_response)
        if matches:
            result: dict[str, str] = {}
            for filename, content in matches:
                result[filename.strip()] = content.strip("\n")
            return result

        # Fallback: markdown fences — try to recover a filename from the fence
        # info string or a leading comment inside the block.
        fence_pattern = re.compile(
            r'```[a-zA-Z]*[ \t]*([^\n`]*)\n(.*?)```',
            re.DOTALL,
        )
        recovered: dict[str, str] = {}
        for fence_info, body in fence_pattern.findall(llm_response):
            fence_info = fence_info.strip()
            body = body.strip("\n")
            # Derive filename: from fence info line, or first comment/shebang line
            filename = ""
            if re.match(r'[\w\-./]+\.\w+', fence_info):
                filename = fence_info
            else:
                first_line = body.splitlines()[0] if body else ""
                m = re.match(r'#\s*([\w\-./]+\.\w+)', first_line)
                if m:
                    filename = m.group(1)
            if filename:
                recovered[filename] = body

        if recovered:
            return recovered

        raise ValueError(
            "No <file name=...><content>...</content></file> blocks found "
            f"in LLM response. Response preview: {llm_response[:300]!r}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_initial_user(spec: dict, backend_lang: str) -> str:
    identity = spec.get("identity", {})
    provenance = spec.get("provenance", {})
    canonical_name = identity.get("canonical_name", "unknown")

    lines: list[str] = []

    lines.append(f"## Library: {canonical_name}  |  Language: {backend_lang}")
    lines.append("")

    # Public documentation and clean-room constraints
    derived = provenance.get("derived_from", [])
    not_derived = provenance.get("not_derived_from", [])
    if derived:
        lines.append("## Public documentation (derive your implementation from these only)")
        for d in derived:
            lines.append(f"  - {d}")
        lines.append("")
    if not_derived:
        lines.append("## Do NOT use (clean-room constraint)")
        for nd in not_derived:
            lines.append(f"  - {nd}")
        lines.append("")

    # Notes from provenance (useful context)
    notes = provenance.get("notes", [])
    if isinstance(notes, str):
        notes = [notes] if notes else []
    if notes:
        lines.append("## Specification notes")
        for note in notes:
            lines.append(f"  {note}")
        lines.append("")

    # Required API surface — functions
    functions = spec.get("functions", {})
    if functions:
        lines.append("## Required API surface — functions")
        lines.append(_format_functions(functions))
        lines.append("")

    # Required API surface — constants
    constants = spec.get("constants", {})
    if constants:
        lines.append("## Required API surface — constants")
        lines.append(_format_constants(constants))
        lines.append("")

    # Wire formats
    wire_formats = spec.get("wire_formats", {})
    if wire_formats:
        lines.append("## Wire formats")
        lines.append(json.dumps(wire_formats, indent=2))
        lines.append("")

    # Error model
    error_model = spec.get("error_model", {})
    if error_model:
        lines.append("## Error model")
        lines.append(json.dumps(error_model, indent=2))
        lines.append("")

    # Behavioral invariants
    invariants = spec.get("invariants", [])
    lines.append(f"## Behavioral invariants ({len(invariants)} total)")
    lines.append(
        "Your implementation MUST satisfy all of these. "
        "Format: id | kind | description | spec"
    )
    for inv in invariants:
        inv_id = inv.get("id", "?")
        kind = inv.get("kind", "?")
        desc = inv.get("description", "")
        spec_dict = inv.get("spec", {})
        lines.append(
            f"  {inv_id} | {kind} | {desc} | {json.dumps(spec_dict, separators=(',', ':'))}"
        )
    lines.append("")

    # Deliverable instructions
    lines.append("## Deliverable")
    lines.append(_deliverable_instructions(canonical_name, backend_lang, spec))

    return "\n".join(lines)


def _build_revision_user(
    spec: dict,
    backend_lang: str,
    previous_source: dict[str, str],
    failed_invariants: list[dict],
    iteration: int,
) -> str:
    identity = spec.get("identity", {})
    canonical_name = identity.get("canonical_name", "unknown")
    invariants = spec.get("invariants", [])
    total = len(invariants)
    failing_ids = {f["id"] for f in failed_invariants}
    passing_count = total - len(failed_invariants)

    lines: list[str] = []

    lines.append(
        f"## Revision request (iteration {iteration}) for: {canonical_name}  "
        f"Language: {backend_lang}"
    )
    lines.append("")
    lines.append("## Previous implementation")
    for filename, content in previous_source.items():
        lines.append(f'<file name="{filename}"><content>')
        lines.append(content)
        lines.append("</content></file>")
    lines.append("")

    lines.append(
        f"## Failing invariants ({len(failed_invariants)} of {total} — "
        f"{passing_count} passing)"
    )
    for f in failed_invariants:
        lines.append(f"  ID:      {f['id']}")
        lines.append(f"  Error:   {f.get('message', '')}")
        # Include the original invariant spec for context
        for inv in spec.get("invariants", []):
            if inv.get("id") == f["id"]:
                lines.append(
                    f"  Kind:    {inv.get('kind', '?')}"
                )
                lines.append(
                    f"  Spec:    {json.dumps(inv.get('spec', {}), separators=(',', ':'))}"
                )
                break
        lines.append("")

    lines.append(
        "Fix ONLY the failing invariants above. "
        "Do not break the passing invariants. "
        "Return complete revised source files using the same file block format."
    )
    lines.append("")
    lines.append("## Deliverable")
    lines.append(_deliverable_instructions(canonical_name, backend_lang, spec))

    return "\n".join(lines)


def _deliverable_instructions(
    canonical_name: str, backend_lang: str, spec: dict
) -> str:
    """Return the file-format instruction paragraph for a given backend."""
    lib_spec = spec.get("library", {})
    esm = lib_spec.get("esm", False)

    if backend_lang == "python":
        return (
            f"Produce a single Python module file named `{canonical_name}.py` "
            f"(or a package directory `{canonical_name}/` with `__init__.py` if needed). "
            "Do NOT import the real library — implement everything from scratch.\n"
            "Wrap output in:\n"
            '<file name="FILENAME"><content>\n'
            "...file content...\n"
            "</content></file>"
        )
    if backend_lang == "c":
        return (
            f"Produce one C source file `{canonical_name}.c` and one header "
            f"`{canonical_name}.h`. The .c file must compile to a shared library "
            f"exporting the required symbols. Do not link against the real library.\n"
            "Wrap output in:\n"
            '<file name="FILENAME"><content>\n'
            "...file content...\n"
            "</content></file>"
        )
    if backend_lang == "javascript":
        module_style = "ESM (export default / export const)" if esm else "CommonJS (module.exports)"
        module_name = lib_spec.get("module_name", canonical_name)
        return (
            f"Produce a single JavaScript file `index.js` using {module_style}.\n"
            f"The harness will mount that file as the Node package `{module_name}`.\n"
            "Do not require/import the real package — implement everything from scratch.\n"
            "Wrap output in:\n"
            '<file name="index.js"><content>\n'
            "...file content...\n"
            "</content></file>"
        )
    if backend_lang == "rust":
        return (
            f"Produce a Rust PyO3 0.22 extension module that Python can `import {canonical_name}`.\n"
            f"Write ONLY `src/lib.rs`. Do NOT produce Cargo.toml or pyproject.toml.\n"
            "Do NOT import or call the real library — implement everything from scratch.\n\n"
            "MANDATORY — follow this EXACT PyO3 0.22 pattern. Any deviation will cause compile errors:\n\n"
            "```rust\n"
            "use pyo3::prelude::*;\n"
            "use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};\n"
            "use pyo3::exceptions::{PyValueError, PyTypeError};\n\n"
            "// --- PyO3 0.22 type-conversion rules (REQUIRED) ---\n"
            "// Rust → Python object:  42i64.to_object(py)  /  3.14f64.to_object(py)  /  \"s\".to_object(py)  /  true.to_object(py)  /  py.None()\n"
            "//   Do NOT use .into_pyobject() — that is PyO3 0.23+ only.\n"
            "// Python → Rust:         obj.extract::<i64>()?  /  obj.extract::<f64>()?  /  obj.extract::<String>()?\n"
            "// Type checks:           obj.is_instance_of::<PyBool>()  /  obj.is_instance_of::<PyInt>()  /  obj.is_instance_of::<PyFloat>()  /  obj.is_instance_of::<PyString>()  /  obj.is_instance_of::<PyList>()  /  obj.is_instance_of::<PyDict>()  /  obj.is_none()\n"
            "// Empty list:            PyList::new_bound(py, std::iter::empty::<PyObject>()).to_object(py)\n"
            "// Append to list:        list_ref.append(item)?  where list_ref: &Bound<'_, PyList>\n"
            "// Empty dict:            PyDict::new_bound(py).to_object(py)\n"
            "// Set dict item:         dict_ref.set_item(key, val)?  where dict_ref: &Bound<'_, PyDict>\n"
            "// Get dict keys:         dict_ref.keys()  (returns Bound<'_, PyList>)\n"
            "// Raise ValueError:      return Err(PyValueError::new_err(\"message\"));\n\n"
            "// --- Module entry point (EXACT signature required) ---\n"
            f"#[pymodule]\nfn {canonical_name}(m: &Bound<'_, PyModule>) -> PyResult<()> {{\n"
            "    // m.add_function(wrap_pyfunction!(my_fn, m)?)?;\n"
            "    // m.add_class::<MyClass>()?;\n"
            "    Ok(())\n"
            "}\n"
            "```\n\n"
            "Wrap your complete src/lib.rs in:\n"
            '<file name="src/lib.rs"><content>\n'
            "...Rust source...\n"
            "</content></file>"
        )
    return (
        "Produce the required source files wrapped in:\n"
        '<file name="FILENAME"><content>\n'
        "...file content...\n"
        "</content></file>"
    )


def _format_functions(functions: dict) -> str:
    """Render the functions section as a compact text table."""
    if not functions:
        return "  (none)"
    lines = []
    for name, info in functions.items():
        if isinstance(info, dict):
            params = info.get("params", info.get("parameters", []))
            ret = info.get("returns", info.get("return", ""))
            param_str = ", ".join(
                f"{p}" if isinstance(p, str) else f"{p.get('name', '?')}: {p.get('type', '?')}"
                for p in (params if isinstance(params, list) else [])
            )
            lines.append(f"  {name}({param_str}) -> {ret}")
        else:
            lines.append(f"  {name}: {info}")
    return "\n".join(lines) if lines else "  (none)"


def _format_constants(constants: dict) -> str:
    """Render the constants section as a compact name=value table."""
    lines = []
    _flatten_constants(constants, lines)
    return "\n".join(lines) if lines else "  (none)"


def _flatten_constants(obj: object, lines: list[str], prefix: str = "") -> None:
    """Recursively flatten nested constants dicts to name=value pairs."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten_constants(v, lines, prefix=f"{prefix}{k}.")
        return
    if isinstance(obj, list):
        for item in obj:
            _flatten_constants(item, lines, prefix=prefix)
        return
    # Scalar — strip trailing dot from prefix
    name = prefix.rstrip(".")
    lines.append(f"  {name} = {obj!r}")
