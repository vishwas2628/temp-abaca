from django.db import models

# This Model represents the "invited_users" m2m relationship between a MilestonePlanner
# and a UserProfile, allowing us to have additional pivot fields (such as is_form_owner)
class UserInvitation(models.Model):
    milestoneplanner = models.ForeignKey('MilestonePlanner', on_delete=models.CASCADE)
    userprofile = models.ForeignKey('viral.UserProfile', on_delete=models.CASCADE) 
    is_form_owner = models.BooleanField(default=False)

    class Meta:
        db_table = 'milestone_planner_milestoneplanner_invited_users'
        unique_together = ('milestoneplanner', 'userprofile')
