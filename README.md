# JobSearch Agent

An intelligent job search automation system with LinkedIn scraping, AI-powered CV generation, and cover letter creation. Runs automatically 3x daily via GitHub Actions.

## Quick Start

```bash
git clone https://github.com/Charank18/JobSearch-Agent.git
cd JobSearch-Agent
pip install -r requirements.txt
playwright install chromium
```

Create a `.env` file with your credentials (see `.env.example`).

### Search Jobs

```bash
python main.py search "Software Engineer" -l "Bangalore, India" -m 10 --generate-cv --generate-cover-letter
```

### Start API Server

```bash
python main_api.py
# Visit http://localhost:8000/docs
```

### Run Tests

```bash
python test_comprehensive.py
```

## GitHub Actions

The workflow runs automatically 3 times daily (6 AM, 2 PM, 10 PM IST) searching for:
- Software Engineer
- Python Developer
- Full Stack Developer
- Machine Learning Engineer

Across major Indian cities. Results are committed back to the repo and available as artifacts.

### Required Secrets

Set these in your GitHub repo Settings > Secrets:
- `LINKEDIN_USERNAME`
- `LINKEDIN_PASSWORD`
- `GOOGLE_API_KEY`

## Project Structure

```
JobSearch-Agent/
??? main.py              # CLI interface
??? main_api.py          # FastAPI server
??? src/
?   ??? agents/          # AI agents (CV, cover letter, parser)
?   ??? scraper/         # LinkedIn & BugMeNot scrapers
?   ??? prompts/         # AI prompt templates
?   ??? utils/           # Pipeline, database, file utilities
??? config/              # YAML configuration files
??? data/                # Resume data and templates
??? .github/workflows/   # Automated job search workflow
??? test_comprehensive.py
```

## License

MIT
