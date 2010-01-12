import genshi

from ckan.lib.base import *

class PackageSaver(object):
    '''Use this to validate, preview and save packages to the db.'''
    @classmethod
    def render_preview(cls, fs, original_name, record_id):
        'Renders a package on the basis of a fieldset - perfect for preview'
        # sync the fs without committing
        pkg = cls._preview_pkg(fs, original_name, record_id)
        return genshi.HTML(cls.render_package(pkg))

    @classmethod
    def render_package(cls, pkg):
        'Renders a package'
        c.pkg = pkg
        notes_formatted = ckan.misc.MarkdownFormat().to_html(pkg.notes)
        c.pkg_notes_formatted = genshi.HTML(notes_formatted)
        return render('package/read')

    @classmethod
    def _preview_pkg(cls, fs, original_name, pkg_id):
        '''Previews the POST data (associated with a package edit) to the
        database
        @input c.error
        @input fs      FieldSet with the param data bound to it
        @input original_name Name of the package before this edit
        @input pkg_id Package id
        @return package object
        '''
        assert not fs.session # otherwise the sync will save to the session
        if fs.model:
            print fs.model.resources
        return cls._update(fs, original_name, pkg_id, None, None, commit=False)

    @classmethod
    def commit_pkg(cls, fs, original_name, pkg_id, log_message, author):
        '''Writes the POST data (associated with a package edit) to the
        database
        @input c.error
        @input fs      FieldSet with the param data bound to it
        @input original_name Name of the package before this edit
        @input pkg_id Package id
        '''
        cls._update(fs, original_name, pkg_id, log_message, author, commit=True)

    @classmethod
    def _update(cls, fs, original_name, pkg_id, log_message, author, commit=True):
        if cls._is_spam(log_message):
            error_msg = 'This commit looks like spam'
            # TODO: make this into a UserErrorMessage or the like
            raise Exception(error_msg)

        validation = fs.validate_on_edit(original_name, pkg_id)
        validation_errors = None
        if not validation:
            errors = []            
            for field, err_list in fs.errors.items():
                errors.append("%s: %s" % (field.name, ";".join(err_list)))
            validation_errors = ', '.join(errors)
        try:
            if commit:
                rev = model.repo.new_revision()
                rev.author = author
                rev.message = log_message
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            if commit and not validation_errors:
                model.Session.commit()
            elif validation_errors:
                raise ValidationException(validation_errors, fs)
            else:
                pkg = fs.model
                assert not model.Session.new
                return pkg

    @classmethod
    def _is_spam(cls, log_message):
        if log_message and 'http:' in log_message:
            return True
        return False
