import sys
import json
from flask import render_template
from time import sleep, time
from rq import get_current_job
from app import db, create_app
from app.models import User, Post, Task
from app.emails import send_email
from app.stocks import quote


# create an app for the task worker, which is running in a process different 
# from that of the main app.
app = create_app()
app.app_context().push()


def example(user_id, seconds):
    """
    This function implements a simple example for the purpose of testing Redis 
    RQ.
    """

    job = get_current_job()
    print("Starting a new task for user = {}".format(user_id))

    for i in range(seconds):
        job.meta['progress'] = i * 100.0 / seconds
        job.save_meta()
        print(i)
        sleep(1)

    job.meta['progress'] = 100.0
    job.save_meta()
    print("Task completed.")


def _set_task_progress(progress):
    """
    This helper function passes the progress value to the job meta, and also 
    update notifications for the associated user.
    """

    job = get_current_job()
    if job is not None:
        # pass the progress value to the job and save
        job.meta['progress'] = progress
        job.save_meta()

        # update notifications for the associated user
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {'task_id': task.id, 
                                                     'progress': progress})

        # flag the task as completed if progress >= 100
        if progress >= 100:
            task.complete = True

        # commit all session changes to the database
        db.session.commit()
        

def export_posts(user_id):
    """
    This task function exports all posts of the given user, email them as an 
    attachment to the same user, and record the export progress as it goes.
    """

    try:
        # export all posts of the input user
        user = User.query.get(user_id)
        _set_task_progress(0)
        i = 0
        data = []
        total_posts = user.posts.count()
        for post in user.posts.order_by(Post.timestamp.asc()):
            data.append({'body': post.body,
                         'timestamp': post.timestamp.isoformat() + 'Z'})
            sleep(5)
            i += 1
            _set_task_progress(i * 100 // total_posts)

        # email posts as an attachment to the user
        send_email(subject="[Wei's Investment Research] Your posts", 
                   sender=app.config['ADMINS'][0], 
                   recipients=[user.email], 
                   text_body=render_template('email/export_posts.txt', 
                                             user=user), 
                   html_body=render_template('email/export_posts.html',
                                             user=user), 
                   attachments=[('posts.json', 
                                 'application/json', 
                                 json.dumps({'posts': data}, indent=4))], 
                   sync=True)
    except:
        app.logger.error('Unhandled exceptions', exc_info=sys.exc_info())
    finally:
        _set_task_progress(100)


def _set_quote_data(symbol, quote_data):
    """
    This helper function adds a user notification for the updated quote, and 
    also returns a boolean value for whether to end the task.
    """
    
    job = get_current_job()
    if job is not None:
        task = Task.query.get(job.get_id())

        # check if the client is actively requesting new quotes
        last_ajax_timestamp = job.meta.get(
            'task_{}_last_ajax_timestamp'.format(job.get_id()))
        # TODO change the if condition below after debugging
        # if last_ajax_timestamp - time() > 60:
        if False:
            task.complete = True
            return True

        # add notifications for the updated quote
        task.user.add_notification(
            name='refresh_quote', data={'symbol': symbol, 'quote': quote_data})
        db.session.commit()

        return False


def refresh_quotes(user_id, symbols, seconds):
    """
    This function fetches the latest stock quotes given the input symbols, and 
    added the updated quote data to user notifications.
    """

    try:
        i = 0
        total = len(symbols)
        while True:
            quote_data = quote(symbols[i])
            end_task = _set_quote_data(symbols[i], quote_data)
            if end_task:
                break
            i += 1
            if i > total - 1:
                i = 0
            sleep(seconds)
    except:
        app.logger.error('Unhandled exceptions', exc_info=sys.exc_info())
    finally:
        pass
