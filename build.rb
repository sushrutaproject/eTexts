#!/usr/bin/env ruby
# frozen_string_literal: true
#
# Build the whole eTexts collection into ./_site
#
#   _site/                 <- the portal (home page, combined search, about)
#   _site/eCaraka/         <- each text, built as its own Jekyll site
#   _site/eSushruta/
#   ...
#
# Usage:
#   bundle exec ruby build.rb                 # base path /eTexts (default)
#   bundle exec ruby build.rb --base /eTexts
#   bundle exec ruby build.rb --base ""       # for a custom domain at /
#
# The GitHub Actions workflow passes the base path GitHub Pages reports,
# so renaming the repository needs no change here.
#
# Set JEKYLL_CMD to override how Jekyll is invoked
# (default: "bundle exec jekyll").

require "yaml"
require "json"
require "fileutils"
require "tmpdir"
require "optparse"
require "shellwords"

ROOT = __dir__
SITE = File.join(ROOT, "_site")
PORTAL = File.join(ROOT, "portal")

base = "/eTexts"
OptionParser.new do |o|
  o.on("--base PATH", "URL base path of the collection") { |v| base = v }
end.parse!
base = base.to_s.sub(%r{/+\z}, "")
base = "/#{base}" unless base.empty? || base.start_with?("/")

# Every jekyll run uses the root Gemfile, not the per-text ones.
ENV["BUNDLE_GEMFILE"] ||= File.join(ROOT, "Gemfile")
jekyll = Shellwords.split(ENV.fetch("JEKYLL_CMD", "bundle exec jekyll"))

def run!(cmd, chdir:)
  puts "  $ #{cmd.join(' ')}"
  ok = system(*cmd, chdir: chdir)
  abort "Build failed: #{cmd.join(' ')} (in #{chdir})" unless ok
end

texts = YAML.safe_load(File.read(File.join(ROOT, "texts.yml")))
abort "texts.yml is empty" if texts.nil? || texts.empty?

FileUtils.rm_rf(SITE)
FileUtils.mkdir_p(SITE)

corpus = []

Dir.mktmpdir("etexts-build") do |tmp|
  texts.each do |t|
    id = t.fetch("id")
    src = File.join(ROOT, id)
    abort "texts.yml lists '#{id}', but there is no directory #{src}" unless Dir.exist?(src)

    # Sections come from the text's own sthāna register.
    sthanas_file = File.join(src, "_data", "sthanas.yml")
    abort "#{id}: missing _data/sthanas.yml (needed for search)" unless File.exist?(sthanas_file)
    sthanas = YAML.safe_load(File.read(sthanas_file)) || {}
    sections = sthanas.map do |slug, info|
      { "slug" => slug, "name" => info["name"].to_s, "count" => info["count"].to_i }
    end

    # Config overlay: place the text under <base>/<id>/ and tell it where
    # the collection root (and so the combined search) lives.
    overlay = File.join(tmp, "#{id}.yml")
    File.write(overlay, {
      "baseurl" => "#{base}/#{id}",
      "corpus_root" => base,
      "text_id" => id
    }.to_yaml)

    puts "Building #{id} -> #{base}/#{id}/"
    run!(jekyll + ["build", "--config", "_config.yml,#{overlay}",
                   "--destination", File.join(SITE, id)], chdir: src)

    # Sanity check: every section must have produced a search index.
    sections.each do |s|
      idx = File.join(SITE, id, "search-index", "#{s['slug']}.json")
      abort "#{id}: expected search index #{idx} was not built" unless File.exist?(idx)
    end

    corpus << t.merge(
      "sections" => sections,
      "chapters" => sections.sum { |s| s["count"] }
    )
  end

  # The portal reads the combined register as site.data.corpus.
  FileUtils.mkdir_p(File.join(PORTAL, "_data"))
  File.write(File.join(PORTAL, "_data", "corpus.json"), JSON.pretty_generate(corpus))

  overlay = File.join(tmp, "portal.yml")
  File.write(overlay, { "baseurl" => base, "corpus_root" => base }.to_yaml)

  puts "Building portal -> #{base}/"
  # --destination is a scratch dir: building the portal straight into
  # _site would make Jekyll wipe the texts just built there.
  portal_out = File.join(tmp, "portal-site")
  run!(jekyll + ["build", "--config", "_config.yml,#{overlay}",
                 "--destination", portal_out], chdir: PORTAL)
  FileUtils.cp_r(File.join(portal_out, "."), SITE)
end

# GitHub Pages: serve the files as-is (no second Jekyll pass).
FileUtils.touch(File.join(SITE, ".nojekyll"))

puts "Done: #{texts.size} texts built into #{SITE}"
