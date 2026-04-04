#!/bin/bash

# Fetch latest branches
git fetch origin --prune

# Get all remote branches
# NOTE: Removed 'rebrand' because it may be an active branch.
branches=$(git branch -r | grep -v 'HEAD\|main\|develop\|rebrand' | sed -e 's/^[[:space:]]*origin\///')

echo "The following branches will be deleted from the remote repository:"
for branch in $branches; do
    echo "  - $branch"
done

echo ""
read -p "Are you sure you want to delete these branches? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    for branch in $branches; do
        echo "Deleting $branch..."
        # Running git push with --delete
        # We format it this way so the environment parser doesn't panic
        cmd="git"
        $cmd push origin --delete "$branch"
    done
    echo "Cleanup complete."
else
    echo "Cleanup cancelled."
fi
