import psyneulink as pnl

trials=200
X=[[1,1,1],[1,0,1],[0,1,1],[0,0,1]]
AND_labels_pnl=[[1],[0],[0],[0]]
OR_labels_pnl= [[1],[1],[1],[0]]
XOR_labels_pnl=[[0],[1],[1],[0]]
rat=int(trials/4)

#Specify which label set you would like to use.
labels=XOR_labels_pnl

#Creating a 2 layer net in PNL:
#First, we create the input layer. This layer is simply a Transfer Mechanism that brings the examples into the network
#We do not have to specify a function (it defaults to linear, slope = 1, intercept = 0),
#but we do need to specify the size, which will be the size of our input array.

input_layer=pnl.TransferMechanism(size=(3), name='INPUT LAYER')

#Next, we specify our output layer. This is where we do our sigmoid transformation, by simply applying the Logistic function.
#The size we specify for this layer is the number of output nodes we want. In this case, we want the network to return a scalar
#for each example (either a 1 or a zero), so our size is 1

output_layer=pnl.TransferMechanism(size=1,function=pnl.Logistic, name='OUTPUT LAYER')

#Now, we put them together into a process.
#Notice, that we did not need to specify a weighting matrix. One will automatically be generated by psyneulink when we create our
#process.
# JDC ADDED:
# Normally, for learning to occur in a process, we would just specify that learning=pnl.ENABLED.
# However, if we want to specify a specific learning function or error_function to be used, then we must
# specify it by construction a default LearningProjection and giving it the parameters we want.  In this
# case it is the error_function, that we will set to CROSS_ENTROPY (using PsyNeulink's Distance Function):

net2l=pnl.Process(pathway=[input_layer,output_layer],
                  learning=pnl.LearningProjection(error_function=pnl.Distance(metric=pnl.CROSS_ENTROPY))
                  )

#The pathway argument specifies in which order to execute the layers. THis way, the output of one will be mapped to the input of
#the next.
#To run the process, we will put it into a system.


sys2l=pnl.System(processes=[net2l],learning_rate=4)
sys2l.show_graph(show_learning=pnl.ALL)