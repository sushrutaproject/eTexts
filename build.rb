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
# (default: "bundle exec jekyll"), and PYTHON for the TEI converter
# (default: "python3").
#
# Two kinds of text are built:
#   * hand-built Jekyll sites (a folder with its own _config.yml), and
#   * TEI texts: a folder holding just a TEI file (plus, optionally, a
#     text.yml). These are converted to a Jekyll site at build time by
#     tools/tei2site.py, and found automatically: a new folder with a TEI
#     file in it is all it takes to add a text.
# A TEI text that cannot be converted or built is left out with an error
# in the log; the rest of the collection is still published.

require "yaml"
require "json"
require "fileutils"
require "tmpdir"
require "optparse"
require "shellwords"
require "open3"

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

python = Shellwords.split(ENV.fetch("PYTHON", "python3"))

def run!(cmd, chdir:)
  puts "  $ #{cmd.join(' ')}"
  ok = system(*cmd, chdir: chdir)
  abort "Build failed: #{cmd.join(' ')} (in #{chdir})" unless ok
end

def run?(cmd, chdir:)
  puts "  $ #{cmd.join(' ')}"
  system(*cmd, chdir: chdir)
end

# Report a problem with one text without stopping the whole build.
# On GitHub the ::error line shows as an annotation on the workflow run.
def text_error(id, msg)
  warn "::error title=eTexts: #{id} left out::#{msg}"
  warn "*** #{id} was NOT added to the site: #{msg}"
end

# Folders that are not texts.
NOT_TEXTS = %w[portal tools vendor node_modules].freeze

def tei_folder?(dir)
  return false if File.exist?(File.join(dir, "_config.yml"))
  Dir.glob(File.join(dir, "*.xml")).any? do |f|
    head = File.open(f, "rb") { |io| io.read(4000) }.to_s
    head.include?("<TEI") || head.include?("tei-c.org")
  end
end

texts = YAML.safe_load(File.read(File.join(ROOT, "texts.yml"))) || []

# TEI folders not (yet) listed in texts.yml are added after the listed
# texts, in alphabetical order. Listing one in texts.yml (just `- id: X`)
# fixes its place in the order, and can override what is shown about it.
listed = texts.map { |t| t["id"] }
Dir.children(ROOT).sort.each do |name|
  next if name.start_with?(".", "_") || NOT_TEXTS.include?(name) || listed.include?(name)
  dir = File.join(ROOT, name)
  texts << { "id" => name } if File.directory?(dir) && tei_folder?(dir)
end
abort "No texts found" if texts.empty?

FileUtils.rm_rf(SITE)
FileUtils.mkdir_p(SITE)

corpus = []

Dir.mktmpdir("etexts-build") do |tmp|
  texts.each do |t|
    id = t.fetch("id")
    src = File.join(ROOT, id)
    abort "texts.yml lists '#{id}', but there is no directory #{src}" unless Dir.exist?(src)

    from_tei = tei_folder?(src)
    if from_tei
      # Convert the TEI file into a Jekyll site in the scratch directory.
      gen = File.join(tmp, "gen", id)
      meta_file = File.join(tmp, "gen", "#{id}.json")
      FileUtils.mkdir_p(File.dirname(gen))
      puts "Converting #{id} from TEI"
      cmd = python + [File.join(ROOT, "tools", "tei2site.py"), src, gen, "--meta", meta_file]
      output, status = Open3.capture2e(*cmd, chdir: ROOT)
      puts output
      unless status.success?
        reason = output.lines.map(&:strip).reject(&:empty?).last || "unknown error"
        text_error(id, "its TEI file could not be converted: #{reason}")
        next
      end
      output.each_line do |line|
        next unless line.include?("WARNING")
        warn "::warning title=eTexts: #{id}::#{line.strip.sub(/^\s*\[[^\]]*\]\s*/, '')}"
      end
      # What texts.yml says about the text wins over what the TEI header says.
      t = JSON.parse(File.read(meta_file)).merge(t.reject { |_, v| v.nil? })
      src = gen
    end

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
    cmd = jekyll + ["build", "--config", "_config.yml,#{overlay}",
                    "--destination", File.join(SITE, id)]
    if from_tei
      unless run?(cmd, chdir: src)
        FileUtils.rm_rf(File.join(SITE, id))
        text_error(id, "Jekyll could not build the site generated from its TEI file")
        next
      end
    else
      run!(cmd, chdir: src)
    end

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

puts "Done: #{corpus.size} of #{texts.size} texts built into #{SITE}"
