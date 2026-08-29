use pyo3::prelude::*;
use pyo3::types::PyList;
use jwalk::{DirEntry, WalkDir};
use std::path::Path;

fn skip_dir(path: &Path) -> bool {
    let mut cur = path;
    loop {
        if let Some(name) = cur.file_name().and_then(|s| s.to_str()) {
            if matches!(name, "proc" | "sys" | "dev" | "run") && cur.parent() == Some(Path::new("/"))
            {
                return true;
            }
        }
        match cur.parent() {
            Some(p) if p != cur => cur = p,
            _ => break,
        }
    }
    false
}

/// Return list of (path, size, is_dir) for a tree walk. Directories have size 0 here;
/// Python rolls up children. Virtual filesystems under /proc /sys /dev /run are skipped.
#[pyfunction]
fn walk_flat(py: Python<'_>, root: String) -> PyResult<Py<PyList>> {
    let mut rows: Vec<(String, u64, bool)> = Vec::new();
    let root_path = Path::new(&root);
    for entry in WalkDir::new(&root)
        .skip_hidden(false)
        .follow_links(false)
        .process_read_dir(|_depth, _path, _state, children| {
            children.retain(|child| match child {
                Ok(e) => {
                    let p = e.path();
                    !skip_dir(&p)
                }
                Err(_) => true,
            });
        })
    {
        let Ok(ent): Result<DirEntry<((), ())>, _> = entry else {
            continue;
        };
        let path = ent.path();
        if skip_dir(&path) {
            continue;
        }
        let is_dir = ent.file_type().is_dir();
        let size = if is_dir {
            0
        } else {
            ent.metadata().map(|m| m.len()).unwrap_or(0)
        };
        rows.push((path.to_string_lossy().into_owned(), size, is_dir));
        if rows.len() % 50_000 == 0 {
            py.check_signals()?;
        }
    }
    if !rows.iter().any(|(p, _, d)| p == &root && *d) {
        rows.push((root_path.to_string_lossy().into_owned(), 0, true));
    }
    let list = PyList::empty(py);
    for (p, sz, d) in rows {
        list.append((p, sz, d))?;
    }
    Ok(list.unbind())
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(walk_flat, m)?)?;
    Ok(())
}
