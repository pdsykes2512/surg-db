#!/bin/bash
# Install required R packages for API-based RStudio integration

echo "Installing R packages for RStudio API integration..."

# Run as rstudio-user with proper HOME directory
sudo -u rstudio-user HOME=/home/rstudio-user R --vanilla --slave << 'EOF'
# Set library path
.libPaths("/home/rstudio-user/R/x86_64-pc-linux-gnu-library/4.5")

# Install packages
packages <- c('httr', 'jsonlite', 'dplyr')

for (pkg in packages) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    cat(sprintf("Installing %s...\n", pkg))
    install.packages(pkg, repos='https://cloud.r-project.org/', dependencies=TRUE, quiet=FALSE)
  } else {
    cat(sprintf("✓ %s already installed\n", pkg))
  }
}

cat("\n✓ All required packages installed!\n")
cat("\nPackages installed:\n")
cat("  - httr (for API requests)\n")
cat("  - jsonlite (for JSON parsing)\n")
cat("  - dplyr (for data manipulation)\n")
EOF

echo ""
echo "Installation complete!"
echo ""
echo "Test with:"
echo "  source('~/R/impactdb/impactdb.R')"
