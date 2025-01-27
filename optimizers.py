import theano
import numpy as np
import theano.tensor as T

DTYPE_FLOATX = theano.config.floatX


class Optimizers(object):
    def __init__(self, name=None):
        self.name = name

    def sgd_updates(self, params, grads, learning_rate=1e-3):
        """
        sgd_updates func

        Stochastic Gradient Descent (SGD)
            Generates update expressions of the form:
            param := param - learning_rate * gradient

        Parameters
        ----------
        params : `list` of shared variables
            The variables to generate update expressions for\n
        grads : `list` of shared variables
            The update expressions for each variable\n
        learning_rate : `float` or symbolic scalar
            The learning rate controlling the size of update steps\n

        Returns
        -------
        updates:
            Specify how to update the parameters of the model as a list of
            (variable, update expression)
        """
        # given two lists of the same length, A = [a1, a2, a3, a4] and
        # B = [b1, b2, b3, b4], zip generates a list C of same size, where each
        # element is a pair formed from the two lists :
        # C = [(a1, b1), (a2, b2), (a3, b3), (a4, b4)]
        updates = []
        for param, grad in zip(params, grads):
            updates.append((param, param - learning_rate * grad))

        return updates

    def rmsprop_updates(self, params, grads, learning_rate=1e-3, rho=0.9,
                        e=1e-8):
        """
        rmsprop_updates func

        RMSProp
            Divide the gradient by a running average of its recent magnitude
            accu_new := rho * accu + (1 - rho) * gradient^2
            rmsprop := - learning rate * grad / sqrt(accu_new + e)
            param_new := param + rmsprop

        Parameters
        ----------
        params : `list` of shared variables
            The variables to generate update expressions for
        grads : `list` of shared variables
            The update expressions for each variable
        learning_rate : `float` or symbolic scalar
            The learning rate controlling the size of update steps
        rho : `float` or symbolic scalar
            Gradient moving average decay factor
        e : `float` or symbolic scalar
            Small value added for numerical stability
        nesterov : `boolean`
            Whether to apply the Nesterov Accelerated Gradient momentum
            v_new := momentum * velocity + rmsprop
            nesterov := v_new + momentum * (v_new - velocity)
            param_new := param + nesterov

        Returns
        -------
        updates:
            Specify how to update the parameters of the model as a list of
            (variable, update expression)
        """
        updates = []
        for param, grad in zip(params, grads):
            size = param.shape.eval()
            # accumulator
            accu = theano.shared(
                value=np.zeros(shape=size, dtype=theano.config.floatX),
                name='accu'
            )
            # update accumulator
            accu_new = rho * accu + (1. - rho) * T.sqr(grad)
            updates.append((accu, accu_new))

            # RMSProp
            rmsgrad = T.maximum(T.sqrt(accu_new), e)
            inc = - learning_rate * grad / rmsgrad
            updates.append((param, param + inc))

        return updates

    def momentum_updates(self, params, grads, learning_rate=1e-3, m=0.9,
                         nesterov=True):
        """
        momentum_updates func

        SGD with Nesterov Accelerated Gradient (NAG) momentum

        Parameters
        ----------
        params : `list` of shared variables
            The variables to generate update expressions for
        grads : `list` of shared variables
            The update expressions for each variable
        learning_rate : `float` or symbolic scalar
            The learning rate controlling the size of update steps
        m : `float` or symbolic scalar
            The momentum rate of the velocity vector

        Returns
        -------
        updates:
            Specify how to update the parameters of the model as a list of
            (variable, update expression)
        """
        updates = []
        lr = learning_rate * (1 - m)
        for param, grad in zip(params, grads):
            size = param.eval().shape
            # momentum velocity
            v = theano.shared(
                value=np.zeros(size, DTYPE_FLOATX),
                name='v_0'
            )
            # velocity update
            inc = m * v - lr * grad
            updates.append((v, inc))

            # Nesterov accelerated momentum
            if nesterov:
                inc = m * inc - lr * grad
            updates.append((param, param + inc))

        return updates

    def adam_updates(self, params, grads, lr=1e-3, b1=0.9, b2=0.999, e=1e-8,
                     amsgrad=True):
        """
        adam_updates func

        Notes
        -----
        Adam optimizer
            Adam - A Method for Stochastic Optimization
            (http://arxiv.org/abs/1412.6980v8)
        AMSGrad modification
            On the Convergence of Adam and Beyond
            (https://openreview.net/forum?id=ryQu7f-RZ)

        Parameters
        ----------
        params : `list` of shared variables
            The variables to generate update expressions for
        grads : `list` of shared variables
            The update expressions for each variable
        learning_rate : `float` or symbolic scalar
            The learning rate controlling the size of update step
        beta1 : `float` or symbolic scalar
            Exponential decay rate for the first moment estimates
        beta2 : `float` or symbolic scalar
            Exponential decay rate for the second moment estimates
        e : `float` or symbolic scalar
            Constant for numerical stability
        amsgrad : `boolean`
            Whether to apply the AMSGrad variant of Adam

        Returns
        -------
        updates:
            Specify how to update the parameters of the model as a list of
            (variable, update expression)
        """
        updates = []
        # initialize timestep
        one = T.constant(1)
        i = theano.shared(np.float32(0.))
        # increment timestep
        i_t = i + 1.
        # adjust learning rate at timestep
        a_t = lr * T.sqrt(one - b2**i_t) / (one - b1**i_t)

        for param, grad in zip(params, grads):
            size = param.eval().shape
            # 1st moment vector
            m = theano.shared(
                value=np.zeros(size, DTYPE_FLOATX),
                name='m_0'
            )
            # 2nd moment vector
            v = theano.shared(
                value=np.zeros(size, DTYPE_FLOATX),
                name='v_0'
            )
            if amsgrad:
                vhat = theano.shared(
                    value=np.zeros(size, DTYPE_FLOATX),
                    name='v_hat'
                )
            # momentum calculation
            m_t = b1 * m + (one - b1) * grad
            v_t = b2 * v + (one - b2) * grad**2
            updates.append((v, v_t))
            updates.append((m, m_t))

            if amsgrad:
                vhat_t = T.maximum(vhat, v_t)
                grad_t = m_t / (T.sqrt(vhat_t) + e)
                updates.append((vhat, vhat_t))
            else:
                grad_t = m_t / (T.sqrt(v_t) + e)

            # Adam update rule
            adam = a_t * grad_t
            updates.append((param, param - adam))

        updates.append((i, i_t))
        return updates
