from datetime import datetime
from PIL import Image
from cStringIO import StringIO
import urllib
import os
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _

class AttachmentManager(models.Manager):
    def attachments_for_object(self, obj):
        object_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type__pk=object_type.id,
                           object_id=obj.id)

class Attachment(models.Model):
    def attachment_upload(instance, filename):
        """Stores the attachment in a "per module/appname/primary key" folder"""
        return 'attachments/%s/%s/%s' % (
            '%s_%s' % (instance.content_object._meta.app_label,
                       instance.content_object._meta.object_name.lower()),
                       instance.content_object.pk,
                       filename)

    objects = AttachmentManager()

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    creator = models.ForeignKey(User, related_name="created_attachments", verbose_name=_('creator'))
    attachment_file = models.FileField(_('attachment'), upload_to=attachment_upload)
    image = models.NullBooleanField(blank=True, null=True, default=None)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)

    class Meta:
        ordering = ['-created']
        permissions = (
            ('delete_foreign_attachments', 'Can delete foreign attachments'),
        )

    def __unicode__(self):
        return '%s attached %s' % (self.creator.username, self.attachment_file.name)

    @property
    def filename(self):
        return os.path.split(self.attachment_file.name)[1]

@receiver(post_save, sender=Attachment, dispatch_uid="check_if_image")
def check_if_image(sender, **kwargs):
    if kwargs.get('raw'): return #loading data from fixture or something
    attachment = kwargs.get('instance')
    if attachment.image is not None:
        #already checked to see if this is an image
        return
    try:
        img_file = urllib.urlopen(attachment.attachment_file.url)
        im = StringIO(img_file.read())
        Image.open(im)
        attachment.image = True
    except IOError:
        attachment.image = False
    attachment.save()

