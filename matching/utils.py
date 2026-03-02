from matching.models.interested_cta import InterestedCTA


def calculate_interest(interested_obj_previous, interested_obj_new):
    # In case the interest is a new one, the value is set to one of them having interest
    if interested_obj_new is None:
        new_val = interested_obj_previous.supporter_is_interested + \
            interested_obj_previous.entrepreneur_is_interested
        interested_obj_previous.state_of_interest = new_val
        interested_obj_previous.save()

        return interested_obj_previous
    else:
        new_supporter_is_interested = interested_obj_new.supporter_is_interested
        new_entrepreneur_is_interested = interested_obj_new.entrepreneur_is_interested
        new_val = new_supporter_is_interested + new_entrepreneur_is_interested

        interested_obj_new.state_of_interest = new_val
        interested_obj_new.save()

    return interested_obj_new
