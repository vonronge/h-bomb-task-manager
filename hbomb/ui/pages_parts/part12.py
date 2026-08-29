ription, u.active, u.enabled, "user" if u.user_unit else "system"))
        return rows

    services = SimpleTablePage(
        "Services",
        ["Name", "Description", "Active", "Load", "Scope"],
        units,
    )
    services.note.setText("User-mode: listing only for system units. Start/stop of system units needs root/polkit and is not persisted here.")

    def starts():
        return [(a.name, a.command, "on" if a.enabled else "off", a.path) for a in list_autostart()]

    startup = SimpleTablePage("Startup apps", ["Name", "Command", "Enabled", "Path"], starts)
    startup.note.setText("Toggle only works for files in ~/.config/autostart.")
    tog = QPushButton("Toggle selected (user files)")

    def do_toggle() -> None:
        items = startup.table.selectedItems()
        if not items:
            return
        row = startup.table.currentRow()
        path = startup.table.item(row, 3).text()
        enabled = startup.table.item(row, 2).text() != "on"
        if toggle_autostart(path, enabled):
            startup.reload()
        else:
            QMessageBox.information(startup, "Startup", "Only user autostart files can be toggled.")

    tog.clicked.connect(do_toggle)
    startup.extra_layout.addWidget(tog)

    def users():
        return [(s.user, s.uid, s.session, s.seat, s.state) for s in list_sessions()]

    users_p = SimpleTablePage("Users", ["User", "UID", "Session", "Seat", "State"], users)

    def info():
        return hardware_tree()

    sysinfo = SimpleTablePage("System Info", ["Key", "Value"], info)

    def apps():
        return [(a.name, a.version, a.source, a.desktop) for a in list_installed_apps()]

    apps_p = SimpleTablePage("Installed Apps", ["Name", "Version", "Source", "Desktop"], apps)
    apps_p.note.setText("Uninstall is not performed here (no root package nuking).")

    def mounts():
        return list_mounts()

    mounts_p = SimpleTablePage("Mounts", ["Mount", "Source", "Type", "Usage"], mounts)

    journal = QWidget()
    jl = QVBoxLayout(journal)
    jl.addWidget(QLabel("Journal"))
    text = QTextEdit()
    text.setReadOnly(True)
    btn = QPushButton("Reload")
    def loadj():
        text.setPlainText("\n".join(journal_tail()))
    btn.clicked.connect(loadj)
    jl.addWidget(btn)
    jl.addWidget(text, 1)

    return {
        "services": services,
        "startup": startup,
        "users": users_p,
        "sysinfo": sysinfo,
        "apps": apps_p,
        "mounts": mounts_p,
        "journal": journal,
    }
