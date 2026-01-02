# Notion Calendar Generator 🗓️

This Python script automates the creation of weekly and daily pages in specific Notion databases. It is designed to set up future planning cycles by establishing relational links between consecutive weeks and mapping daily pages to their corresponding weeks and pre-defined configuration data (HR Zones, Physiological Stats).

The script uses the **Notion API v1** directly via the `requests` library (no third-party SDKs) for precise control.

---

## ⚙️ Configuration & Prerequisites

Before running the script, you must complete two steps:

### 1. Notion Setup

1.  **Create an Integration:** Generate an Internal Integration Token from Notion's "My Integrations" page (it starts with `secret_...`).
2.  **Share Databases:** Share **all four** target databases with your integration. Click the `...` menu on each database, go to "Add connections," and select your integration name.

### 2. Script Setup

The script requires several Database IDs to be configured within the `notion_training_planner.py` file itself (under the `--- CONFIGURATION ---` section), while the execution-specific parameters are provided via command-line arguments.

#### Hardcoded Configuration (in `notion_training_planner.py`)

| Variable | Description |
| :--- | :--- |
| `DB_WEEKLY_CHART` | Database ID for the "Weekly Chart" table. |
| `DB_DAILY_PLANS` | Database ID for the "Daily Plans" calendar. |
| `DB_HR_ZONES` | Database ID for the "HR Zones" configuration table. |
| `DB_PHYSIO_STATS` | Database ID for the "Physiological Stats" configuration table. |

---

## 🚀 How to Run the Script

1.  **Install Dependencies:**
    The script only requires the standard `requests` library.

    ```bash
    pip install requests
    ```

2.  **Execute the Script:**
    Run the script by providing your Notion token, the start date (must be a Monday), and the number of weeks to generate.

    ```bash
    python notion_training_planner.py --token "your_notion_token" --start-date "2026-01-19" --weeks 12
    ```

### Command-line Arguments

| Argument | Description |
| :--- | :--- |
| `--token` | Your Notion Integration Token (`secret_...`). |
| `--start-date` | The starting date for the generation in `YYYY-MM-DD` format. **Must be a Monday.** |
| `--weeks` | The number of consecutive weeks to generate. |

### Execution Flow

The script performs two main phases:

#### Phase 1: Weekly Chart Generation
This phase creates pages in the **Weekly Chart** database.

* **Page Title:** `Week <week_number> <year>`
* **Properties Set:**
    * `Name` (Title)
    * `Week Start` (Date)
    * `Week End` (Date)
    * `Previous Week` (Relation to the previous page created in the loop).
    * `Personal Data` (Relation to the "Data" page in Physiological Stats).
* **Validation:** The starting date (`--start-date`) is strictly checked to ensure it is a Monday.

#### Phase 2: Daily Plans Generation
This phase runs immediately after Phase 1, creating `--weeks * 7` pages in the **Daily Plans** database.

* **Page Title:** The date in `DD.MM.YYYY` format.
* **Properties Set:**
    * `Name` (Title)
    * `Date` (Date property, required for Calendar View display).
    * `Linked Week` (Relation to the correct weekly page created in Phase 1).
    * `Personal Data` (Relation to the "Data" page in Physiological Stats).
    * `Z2`, `Z3`, `Z4`, `Z5` (Relations to the corresponding pages in the HR Zones database).
* **Strict Error Handling:** If the script fails to find any required relational page (e.g., "Data", "Z2"), it will throw a critical error and exit before creating pages.

---

## 🛠️ Notion Database Structure

For the script to work, your database properties must match the names used in the Python file **exactly** (case-sensitive and space-sensitive).

| Database | Expected Properties | Type |
| :--- | :--- | :--- |
| **Weekly Chart** | `Name` | Title |
| | `Week Start` | Date |
| | `Week End` | Date |
| | `Previous Week` | Relation (to Weekly Chart DB) |
| | `Personal Data` | Relation (to Physiological Stats DB) |
| **Daily Plans** | `Name` | Title |
| | `Date` | Date |
| | `Linked Week` | Relation (to Weekly Chart DB) |
| | `Personal Data` | Relation (to Physiological Stats DB) |
| | `Z2`, `Z3`, `Z4`, `Z5` | Relation (to HR Zones DB) |
