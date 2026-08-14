# Customization

## Language

The application interface is English, while the included demo records remain in Russian. Personal and reference row content can use any language.

The validator accepts both English priority labels (`High`, `Medium`, `Low`) and legacy Russian labels (`Высокий`, `Средний`, `Низкий`). Keep each label paired with its CSS class.

## Care materials

The demo soil recipes use materials available to the original owner: universal indoor-plant soil, perlite, expanded clay, and orchid bark. Tell the `plant-tracker` skill which materials you own before asking it to generate or revise recipes.

## Styling

All styles are embedded in `plants.html`. Color variables are near the top of the file. The page is responsive and does not require a build system.

## Fields

The personal table has seven columns: photo, personal name, species, condition, action, priority, and inspection date. The reference has ten care fields.

Changing columns is possible, but update all of the following together:

- table headers and row markup in `plants.html`;
- the `row_pattern` regex in `.agents/skills/plant-tracker/scripts/validate_tracker.py`, which
  hardcodes the column order and will silently stop matching rows if you get it wrong;
- `.agents/skills/plant-tracker/references/tracker-contract.md`.

After any column change, confirm the validator still counts every row. It reports
`OK: 0 plants` rather than an error when its row regex matches nothing, so a broken pattern
looks like a pass.

## Dates

Use ISO dates in markup: `datetime="YYYY-MM-DD"`. Displayed dates may be `YYYY-MM-DD` or the legacy `DD.MM.YYYY` format.

## Priority behavior

- `priority high` for urgent treatment or rescue.
- `priority medium` for a safe pending task.
- `priority` for low priority with an empty action cell.

Rows are sorted by priority and then by plant name when the page loads.
