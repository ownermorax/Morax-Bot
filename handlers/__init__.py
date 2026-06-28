from handlers import business, inline, commands, buttons


def register_all(app, deleted_storage, edited_storage, chats_storage,
                 deleted_chats_storage, db):
    """Register all handlers with the app and shared dependencies."""
    business.register(app, deleted_storage, edited_storage, chats_storage)
    inline.register(app, db)
    commands.register(app, deleted_storage, edited_storage, chats_storage,
                      deleted_chats_storage, db)
    buttons.register(app)