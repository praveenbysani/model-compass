# Contributing to ModelCompass

Corrections, additional models and reproducible comparisons are welcome. Read
[the methodology](METHODOLOGY.md) and search existing issues before contributing.
Discuss larger changes in an issue first.

## Contributions

- Include the exact model/version, relevant date and supporting source URL.
  Prefer provider documentation or original evaluation reports.
- Edit source CSVs in `data/sources/` and regenerate derived files. Preserve
  historical prices and leave unverified values blank.
- Keep category assignments and chart settings consistent. Separate factual
  evidence from opinions and explain any calculations or assumptions.
- Keep pull requests focused. Describe what changed, why and how you checked it.
  For bugs, include steps to reproduce the problem.

For data or chart changes, run these commands from the repository root:

```bash
python scripts/normalize_data.py
python scripts/validate_data.py
python scripts/build_charts.py
python scripts/normalize_data.py --check
```

Include affected generated files. Check chart layouts, hover details and legend
filtering when relevant. Documentation-only changes need no rebuild.

Contribute only material you have permission to share, under the applicable
[project licence](LICENSE). Verify all sources and review automated or
AI-assisted work before submitting it.

## Code of conduct

Be respectful, give constructive feedback and discuss ideas rather than attacking
people. Harassment, discrimination, threats, sharing private information without
permission, spam and retaliation are unacceptable in project spaces.

Report concerns to [@praveenbysani](https://github.com/praveenbysani). For sensitive
reports, request a private contact method without posting incident details
publicly.

Maintainers may close unsupported or duplicate submissions, remove abusive
content and restrict participation. Good-faith technical disagreement is welcome.
