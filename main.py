import jieba
import jsonpickle
import random
import tantivy
import telegram.ext
import traceback

import bottoken
import config
import log


def process_message(message):
    text = ''
    sticker = ''

    if message is not None:
        if message.text:
            text = message.text

        if message.sticker:
            sticker = message.sticker.file_id

    return text, sticker


def is_direct_message(message):
    chat_id = message.chat.id

    if message is not None:
        if message.from_user is not None and message.from_user.id == chat_id:
            return True

    if message.reply_to_message is not None:
        reply = message.reply_to_message

        if reply.from_user is not None and reply.from_user == bottoken.self:
            return True

    return False


def cut_text(text):
    return ' '.join(jieba.cut(text))


def select_doc(hits):
    target = sum(score for score, _ in hits) * random.random()

    for score, address in hits:
        target -= score

        if target < 0:
            return address

    return None


def main():
    # build the search engine

    schema_builder = tantivy.SchemaBuilder()
    schema_builder.add_text_field('last_text', stored=True)
    schema_builder.add_text_field('last_sticker', stored=True)
    schema_builder.add_text_field('text', stored=True)
    schema_builder.add_text_field('sticker', stored=True)
    schema = schema_builder.build()

    index = tantivy.Index(schema)

    # load historical data

    count = 0
    writer = index.writer()
    last_messages = {}

    for update in log.read_log():
        count += 1

        if count % 1000 == 0:
            print('load:', count)

        text, sticker = process_message(update.message)

        if text or sticker:
            chat_id = update.message.chat.id

            if chat_id in last_messages:
                last_text, last_sticker = last_messages[chat_id]

                writer.add_document(
                    tantivy.Document(
                        last_text=cut_text(last_text),
                        last_sticker=last_sticker,
                        text=text,
                        sticker=sticker
                    )
                )

            last_messages[chat_id] = text, sticker

    writer.commit()
    index.reload()

    print('total:', count)
    print('ready')

    # event handlers

    def error_handler(update, context):
        log.error(update, context.error)

    def message_handler(update, _):
        log.log(update)

        try:
            text, sticker = process_message(update.message)

            if (text or sticker) and (
                is_direct_message(update.message)
                or random.random() < config.rate
            ):
                searcher = index.searcher()

                if text:
                    query = index.parse_query(cut_text(text), ['last_text'])
                else:
                    query = index.parse_query(sticker, ['last_sticker'])

                hits = searcher.search(query, 100, False).hits
                address = select_doc(hits)

                if address is not None:
                    doc = searcher.doc(address)

                    print(
                        doc['last_text'][0] or doc['last_sticker'][0],
                        '::',
                        doc['text'][0] or doc['sticker'][0]
                    )

                    if doc['text'][0]:
                        update.message.reply_text(doc['text'][0])
                    else:
                        update.message.reply_sticker(doc['sticker'][0])
        except:
            traceback.print_exc()
            log.error(update, 'internal error')

    # start the bot

    # TODO: remove `use_context=True`
    updater = telegram.ext.Updater(bottoken.token, use_context=True)

    updater.dispatcher.add_error_handler(error_handler)
    updater.dispatcher.add_handler(
        telegram.ext.MessageHandler(
            telegram.ext.filters.Filters.update.message,
            message_handler
        )
    )

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
