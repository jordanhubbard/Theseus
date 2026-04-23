'use strict';

/**
 * Join path segments with '/' separator.
 * @param {...string} segments
 * @returns {string}
 */
function path_join(...segments) {
  return segments.join('/');
}

/**
 * Return the last portion of a path (the filename).
 * @param {string} p
 * @returns {string}
 */
function path_basename(p) {
  const parts = p.split('/');
  return parts[parts.length - 1];
}

/**
 * Return the directory portion of a path.
 * @param {string} p
 * @returns {string}
 */
function path_dirname(p) {
  const lastSlash = p.lastIndexOf('/');
  if (lastSlash === -1) return '.';
  if (lastSlash === 0) return '/';
  return p.slice(0, lastSlash);
}

module.exports = {
  path_join,
  path_basename,
  path_dirname,
};