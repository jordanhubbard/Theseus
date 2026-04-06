#!/bin/bash
# Automated release script for Theseus
# Usage: ./scripts/release.sh [major|minor|patch]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
info() {
    echo -e "${BLUE}[info]  $1${NC}"
}

success() {
    echo -e "${GREEN}[ok]    $1${NC}"
}

warn() {
    echo -e "${YELLOW}[warn]  $1${NC}"
}

error() {
    echo -e "${RED}[error] $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."

    if ! command -v gh &> /dev/null; then
        error "GitHub CLI (gh) is not installed. Install with: brew install gh"
    fi

    if ! gh auth status &> /dev/null; then
        error "GitHub CLI is not authenticated. Run: gh auth login"
    fi

    if [[ -n $(git status --porcelain) ]]; then
        error "Git working directory is not clean. Commit or stash changes first."
    fi

    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$CURRENT_BRANCH" != "main" ]]; then
        error "Not on main branch (currently on: $CURRENT_BRANCH). Switch to main first."
    fi

    success "Prerequisites check passed"
}

# Get current version from git tags
get_current_version() {
    git tag -l 'v*' | sort -V | tail -1 | sed 's/^v//'
}

# Calculate next version
calculate_next_version() {
    local current=$1
    local bump_type=$2

    IFS='.' read -r major minor patch <<< "$current"

    case $bump_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            error "Invalid bump type: $bump_type (use major, minor, or patch)"
            ;;
    esac

    echo "$major.$minor.$patch"
}

# Generate changelog entry from git log
generate_changelog_entry() {
    local prev_version=$1
    local new_version=$2
    local date
    date=$(date +%Y-%m-%d)

    info "Generating changelog from v$prev_version to HEAD..." >&2

    local commits
    if git rev-parse "v$prev_version" &>/dev/null; then
        commits=$(git log "v$prev_version"..HEAD --pretty=format:"%h %s" --no-merges)
    else
        commits=$(git log --pretty=format:"%h %s" --no-merges)
    fi

    local added=""
    local changed=""
    local fixed=""
    local removed=""
    local other=""

    while IFS= read -r line; do
        if [[ $line =~ ^[a-f0-9]+\ feat(\(.*\))?:\ (.*) ]]; then
            added+="- ${BASH_REMATCH[2]}\n"
        elif [[ $line =~ ^[a-f0-9]+\ fix(\(.*\))?:\ (.*) ]]; then
            fixed+="- ${BASH_REMATCH[2]}\n"
        elif [[ $line =~ ^[a-f0-9]+\ refactor(\(.*\))?:\ (.*) ]]; then
            changed+="- ${BASH_REMATCH[2]}\n"
        elif [[ $line =~ ^[a-f0-9]+\ (chore|docs)(\(.*\))?:\ (.*) ]]; then
            other+="- ${BASH_REMATCH[3]}\n"
        else
            local msg
            msg=$(echo "$line" | cut -d' ' -f2-)
            other+="- $msg\n"
        fi
    done <<< "$commits"

    local entry="## [$new_version] - $date\n\n"

    if [[ -n "$added" ]]; then
        entry+="### Added\n$added\n"
    fi
    if [[ -n "$changed" ]]; then
        entry+="### Changed\n$changed\n"
    fi
    if [[ -n "$fixed" ]]; then
        entry+="### Fixed\n$fixed\n"
    fi
    if [[ -n "$removed" ]]; then
        entry+="### Removed\n$removed\n"
    fi
    if [[ -n "$other" ]]; then
        entry+="### Other\n$other\n"
    fi

    echo -e "$entry"
}

# Update CHANGELOG.md
update_changelog() {
    local changelog_entry=$1
    local changelog_file="CHANGELOG.md"

    info "Updating $changelog_file..."

    if [[ ! -f "$changelog_file" ]]; then
        error "CHANGELOG.md not found. Expected at repo root."
    fi

    local temp_file entry_file
    temp_file=$(mktemp)
    entry_file=$(mktemp)

    echo -e "$changelog_entry" > "$entry_file"

    awk '
        /^## \[Unreleased\]/ {
            print $0
            print ""
            while ((getline line < "'"$entry_file"'") > 0) {
                print line
            }
            close("'"$entry_file"'")
            next
        }
        { print }
    ' "$changelog_file" > "$temp_file"

    mv "$temp_file" "$changelog_file"
    rm "$entry_file"

    success "CHANGELOG.md updated"
}

# Create git tag and GitHub release
create_release() {
    local version=$1
    local prev_version=$2
    local test_status=$3

    info "Creating release v$version..."

    local release_notes commit_count
    if git rev-parse "v$prev_version" &>/dev/null; then
        release_notes=$(git log "v$prev_version"..HEAD --pretty=format:"- %s" --no-merges)
        commit_count=$(git rev-list --count "v$prev_version"..HEAD)
    else
        release_notes=$(git log --pretty=format:"- %s" --no-merges)
        commit_count=$(git rev-list --count HEAD)
    fi

    local compare_url=""
    if [[ -n "${REPO_URL:-}" ]]; then
        compare_url="${REPO_URL}/compare/v${prev_version}...v${version}"
    fi

    cat > /tmp/release_notes.md << EOF
## Theseus v$version

### Statistics
- **Commits since v$prev_version**: $commit_count
- **Test Status**: $test_status

### Changes

$release_notes
EOF
    if [[ -n "$compare_url" ]]; then
        printf '\n### Links\n- [Full Changelog](%s)\n- [Documentation](%s/tree/main/docs)\n\n---\n\n**Full Changelog**: %s\n' \
            "$compare_url" "${REPO_URL}" "$compare_url" >> /tmp/release_notes.md
    fi

    info "Committing CHANGELOG.md..."
    git add CHANGELOG.md
    if git diff --cached --quiet; then
        info "CHANGELOG.md already up to date, skipping commit"
    else
        git commit -m "docs: Update CHANGELOG for v$version release"
    fi

    info "Syncing with origin before tagging..."
    git pull --rebase origin main

    info "Creating git tag v$version..."
    git tag -a "v$version" -m "Release v$version"

    info "Pushing to origin..."
    git push origin main
    git push origin "v$version"

    info "Creating GitHub release..."
    gh release create "v$version" \
        --title "v$version" \
        --notes-file /tmp/release_notes.md

    rm /tmp/release_notes.md

    success "Release v$version created successfully!"
}

# Main
main() {
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║   Theseus Automated Release Script       ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""

    check_prerequisites

    CURRENT_VERSION=$(get_current_version)
    REPO_URL=$(gh repo view --json url -q .url 2>/dev/null || echo "")

    if [[ -z "$CURRENT_VERSION" ]]; then
        CURRENT_VERSION="0.0.0"
        info "No prior tags found — this will be the first release (v1.0.0)"
    else
        info "Current version: v$CURRENT_VERSION"
    fi

    BUMP_TYPE=${1:-patch}
    if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
        error "Invalid argument: $BUMP_TYPE (use major, minor, or patch)"
    fi

    NEXT_VERSION=$(calculate_next_version "$CURRENT_VERSION" "$BUMP_TYPE")

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Current: v$CURRENT_VERSION"
    echo "  Next:    v$NEXT_VERSION ($BUMP_TYPE)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    CHANGELOG_ENTRY=$(generate_changelog_entry "$CURRENT_VERSION" "$NEXT_VERSION")

    info "Generated changelog entry:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "$CHANGELOG_ENTRY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    update_changelog "$CHANGELOG_ENTRY"

    info "Running tests..."
    local test_output_file
    test_output_file=$(mktemp)
    if ! make test > "$test_output_file" 2>&1; then
        cat "$test_output_file"
        rm -f "$test_output_file"
        error "Tests failed. Fix tests before releasing."
    fi
    success "Tests passed"

    local test_status
    test_status=$(grep -E "passed|failed|error" "$test_output_file" | tail -1 || echo "All tests passed")
    rm -f "$test_output_file"

    create_release "$NEXT_VERSION" "$CURRENT_VERSION" "$test_status"

    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║    Release Complete!                     ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""
    if [[ -n "${REPO_URL:-}" ]]; then
        echo "  ${REPO_URL}/releases/tag/v${NEXT_VERSION}"
        echo ""
    fi
}

main "$@"
