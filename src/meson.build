pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'hatchet'
gnome = import('gnome')

blueprints = custom_target('blueprints',
  input: files(
    'shortcuts-dialog.blp',
    'window.blp',
    'picker.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '--minify', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

gnome.compile_resources('hatchet',
  'hatchet.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: blueprints,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'hatchet.in',
  output: 'hatchet',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

hatchet_sources = [
  '__init__.py',
  'main.py',
  'util.py',
  'context.py',
  'window.py',
  'picker.py',
  'emacs.py',
]

install_data(hatchet_sources, install_dir: moduledir)
