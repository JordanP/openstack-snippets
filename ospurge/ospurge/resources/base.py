import abc
import logging
from inspect import signature


class MatchSignaturesMeta(type):
    def __init__(self, clsname, bases, clsdict):
        super().__init__(clsname, bases, clsdict)
        sup = super(self, self)
        for name, value in clsdict.items():
            if name.startswith('_') or not callable(value):
                continue
            # Get the previous definition (if any) and compare the signatures
            prev_dfn = getattr(sup, name, None)
            if prev_dfn:
                prev_sig = signature(prev_dfn)
                val_sig = signature(value)
                if prev_sig != val_sig:
                    logging.warning('Signature mismatch in %s. %s != %s',
                                    value.__qualname__, prev_sig, val_sig)


MatchSignaturesMetaWithAbcMixin = type('MatchSignaturesMetaWithAbcMixin',
                                       (abc.ABCMeta, MatchSignaturesMeta), {})


class ServiceResource(metaclass=MatchSignaturesMetaWithAbcMixin):
    def __init__(self, creds_manager):
        """
        :type creds_manager: ospurge.main.CredentialsManager
        """

        if not hasattr(self, 'PRIORITY'):
            raise AttributeError(
                'Class {}.{} must have a "PRIORITY" class attribute'.format(
                    self.__module__, self.__class__.__name__)
            )

        self.cloud = creds_manager.cloud

        if hasattr(creds_manager, 'operator_cloud'):
            self.operator_cloud = creds_manager.operator_cloud

        self.cleanup_project_id = creds_manager.project_id

    @classmethod
    def priority(cls) -> int:
        return cls.PRIORITY

    @abc.abstractmethod
    def list(self):
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, resource):
        raise NotImplementedError

    def should_delete(self, resource):
        project_id = resource.get('project_id', resource.get('tenant_id'))
        if project_id:
            return project_id == self.cleanup_project_id
        else:
            logging.warning("Can't determine owner of resource %s", resource)
            return True

    def check_prerequisite(self):
        pass

    @abc.abstractstaticmethod
    def to_string(resource):
        raise NotImplementedError
